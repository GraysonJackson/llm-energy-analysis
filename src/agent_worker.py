"""Run Python for one task snapshot in a disposable local Docker container."""

import json
import os
import re
import subprocess
from uuid import uuid4


IMAGE = 'python:3.12-slim'
PATH_PATTERN = re.compile(r'(?:[A-Za-z0-9_][A-Za-z0-9_.-]*/)*[A-Za-z0-9_][A-Za-z0-9_.-]*\.(?:py|md|csv)')

# This bootstrap runs inside Docker. Child output is bounded by the file-size limit.
BOOTSTRAP = r'''
import json, os, resource, subprocess, sys
from pathlib import Path
from tempfile import TemporaryFile

request = json.load(sys.stdin)
os.chdir('/work')
for name, content in request['files'].items():
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

def limits():
    resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))

with TemporaryFile(dir='/tmp') as output:
    try:
        result = subprocess.run([sys.executable, '-B', '-E', '-s', *request['args']],
                                input=request['stdin'].encode('utf-8'),
                                stdout=output, stderr=subprocess.STDOUT,
                                env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'LANG': 'C.UTF-8'},
                                user=65534, group=65534, extra_groups=[],
                                timeout=request['seconds'], preexec_fn=limits)
        code = result.returncode
    except subprocess.TimeoutExpired:
        code = 124
    output.seek(0)
    result_text = output.read(8192).decode('utf-8', errors='replace')
print(json.dumps({'exit_code': code, 'output': result_text}))
'''


def docker_command(args, **kwargs):
    try:
        return subprocess.run(['docker', *args], capture_output=True, encoding='utf-8',
                              errors='replace', **kwargs)
    except FileNotFoundError:
        raise RuntimeError('Docker Desktop is required for isolated agent tests') from None


def is_local_endpoint(endpoint):
    return endpoint.startswith(('unix:///', 'npipe:////./pipe/'))


class Worker:
    def __init__(self):
        override = os.environ.get('DOCKER_HOST')
        context = docker_command(['context', 'inspect', '--format', '{{.Endpoints.docker.Host}}'], timeout=10)
        if (context.returncode or not is_local_endpoint(context.stdout.strip())
                or (override and not is_local_endpoint(override))):
            raise RuntimeError('Select a local Docker engine so worker power is measured at this workstation')
        engine = docker_command(['info', '--format', '{{.OSType}}'], timeout=15)
        if engine.returncode or engine.stdout.strip() != 'linux':
            raise RuntimeError('Start Docker Desktop with the Linux engine before running the agent pilot')
        image = docker_command(['image', 'inspect', IMAGE, '--format', '{{.Id}}'], timeout=15)
        self.image = image.stdout.strip()
        if image.returncode or not re.fullmatch(r'sha256:[0-9a-f]{64}', self.image):
            raise RuntimeError(f'Load the worker image first with docker pull {IMAGE}')

    def run(self, files, args, stdin='', seconds=12):
        if any(not PATH_PATTERN.fullmatch(path) for path in files):
            raise ValueError('Invalid path in isolated worker snapshot')
        if seconds <= 0:
            return {'exit_code': 124, 'output': 'Task time expired'}
        name = f'llm-agent-pilot-{uuid4().hex}'
        # Only the trusted bootstrap has the capabilities needed to drop the child's identity.
        command = ['run', '--rm', '--interactive', '--name', name, '--pull=never', '--network=none',
                   '--read-only', '--cap-drop=ALL', '--cap-add=SETUID', '--cap-add=SETGID',
                   '--security-opt=no-new-privileges', '--user', '0:0',
                   '--memory=192m', '--memory-swap=192m', '--cpus=1', '--pids-limit=24', '--log-driver=none',
                   '--tmpfs', '/work:rw,noexec,nosuid,nodev,size=12m,mode=1777',
                   '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=12m,mode=1777',
                   '--entrypoint', 'python', self.image, '-I', '-c', BOOTSTRAP]
        payload = json.dumps({'files': files, 'args': args, 'stdin': stdin, 'seconds': seconds})
        try:
            result = docker_command(command, input=payload, timeout=seconds + 15)
        except (KeyboardInterrupt, subprocess.TimeoutExpired):
            docker_command(['rm', '-f', name], timeout=10)
            raise
        if result.returncode:
            raise RuntimeError(f'Isolated Python worker failed to start or return results (exit {result.returncode})')
        return json.loads(result.stdout)

    def check(self):
        result = self.run({}, ['-c', '''
import os
from pathlib import Path
assert os.geteuid() != 0
assert set(os.listdir('/sys/class/net')) == {'lo'}
assert not {'OPENAI_API_KEY', 'GEMINI_API_KEY', 'SHELLY_IP'} & os.environ.keys()
assert not Path('/var/run/docker.sock').exists()
assert int(next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines()
                if line.startswith('CapEff:')), 16) == 0
try:
    os.open('/proc/1/fd/1', os.O_WRONLY)
except (PermissionError, FileNotFoundError):
    pass
else:
    raise AssertionError('Worker can open the bootstrap output stream')
try:
    Path('/usr/local/pilot_check').write_text('unexpected write')
except OSError:
    pass
else:
    raise AssertionError('Root filesystem is writable')
Path('ok.py').write_text('pass')
print('worker ready')
'''])
        if result != {'exit_code': 0, 'output': 'worker ready\n'}:
            raise RuntimeError('The isolated worker failed its readiness check')
