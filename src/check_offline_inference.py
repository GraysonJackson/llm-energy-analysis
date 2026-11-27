"""Record whether installed Ollama models answer with the Windows uplink or app egress blocked."""

import argparse
import json
import subprocess
from datetime import datetime, timezone

import requests
import yaml

from offline_firewall import OllamaFirewall
from run_direct_pilot import CONTEXT, DEADLINE, KEEP_ALIVE, ROOT, LocalOllama, persist, utc_now


WINDOWS_NETWORK_STATE = r'''
$ErrorActionPreference = 'Stop'
$physical = @(Get-NetAdapter -Physical | Where-Object Status -eq 'Up')
$routes = @(Get-NetRoute | Where-Object { $_.DestinationPrefix -in @('0.0.0.0/0', '::/0') })
@{
  active_physical_adapters = $physical.Count
  default_routes = $routes.Count
} | ConvertTo-Json -Compress
'''


def probe():
    process = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', WINDOWS_NETWORK_STATE],
                             capture_output=True, text=True, timeout=30, check=False)
    if process.returncode:
        raise RuntimeError('Windows could not report network adapter and route state')
    return json.loads(process.stdout)


def disconnected(state):
    return state['active_physical_adapters'] == 0 and state['default_routes'] == 0


def verify(config, report, check_network=probe, session_factory=requests.Session, firewall=False):
    boundary_ok = (lambda state: state['verified']) if firewall else disconnected
    failed = 'firewall_boundary_unverified' if firewall else 'network_connected'
    changed = 'firewall_boundary_changed' if firewall else 'network_reconnected'
    completed = 'completed_firewall_isolated' if firewall else 'completed_offline'
    report['network_before'] = check_network()
    if not boundary_ok(report['network_before']):
        report['status'] = failed
        return False
    host = config['ollama']['host']
    with session_factory() as session:
        ollama = LocalOllama(host, session)
        report['ollama_version'] = ollama.call('/api/version')['version']
        if ollama.call('/api/ps')['models']:
            report['status'] = 'models_already_loaded'
            return False
        installed = {row.get('model') or row.get('name'): row.get('digest') for row in ollama.call('/api/tags')['models']}
        for model in config['ollama']['models']:
            if not boundary_ok(check_network()):
                report['status'] = changed
                return False
            if not installed.get(model):
                report['models'].append({'model': model, 'status': 'missing_model_or_digest'})
                continue
            entry = {'model': model, 'digest': installed[model], 'status': 'request_failed'}
            try:
                raw = ollama.call('/api/generate', {'model': model, 'prompt': report['prompt'], 'stream': False,
                                  'think': 'low' if model.startswith('gpt-oss:') else False, 'keep_alive': KEEP_ALIVE,
                                  'options': {'num_ctx': CONTEXT, 'num_predict': 256}}, timeout=DEADLINE)
                answer = raw.get('response')
                entry['finish_reason'] = raw.get('done_reason')
                entry['answer_is_42'] = isinstance(answer, str) and answer.strip() == '42'
                if raw.get('done') and raw.get('done_reason') != 'length' and isinstance(answer, str) and answer.strip():
                    entry['status'] = 'completed'
                else:
                    entry['status'] = 'incomplete'
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                entry['error_type'] = type(exc).__name__
            finally:
                try:
                    ollama.unload(model)
                except (requests.RequestException, RuntimeError, ValueError):
                    entry['unload_confirmed'] = False
            report['models'].append(entry)
            if entry.get('unload_confirmed') is False:
                break
    report['network_after'] = check_network()
    if not boundary_ok(report['network_after']):
        report['status'] = changed
    elif (report['models'] and len(report['models']) == len(config['ollama']['models'])
          and all(model['status'] == 'completed' and model.get('unload_confirmed') is not False for model in report['models'])):
        report['status'] = completed
    else:
        report['status'] = 'model_checks_incomplete'
    return report['status'] == completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firewall', action='store_true', help='Temporarily block non-loopback outbound traffic for Ollama only')
    args = parser.parse_args()
    config = yaml.safe_load((ROOT / 'config.yaml').read_text(encoding='utf-8'))
    folder = ROOT / 'runs' / datetime.now(timezone.utc).strftime('offline_check_%Y%m%dT%H%M%S_%fZ')
    folder.mkdir(parents=True)
    report = {'started_utc': utc_now(), 'status': 'started', 'models': [], 'prompt': 'Reply with only the number 42.',
              'boundary': ('local Ollama loopback; temporary Windows Firewall outbound rules for Ollama executables'
                           if args.firewall else 'local Ollama loopback; physical adapter and default route snapshots'),
              'scope': 'functional check without metering or packet capture'}
    result = 2
    guard = None
    try:
        if args.firewall:
            guard = OllamaFirewall(config['ollama']['host'])
            report['firewall_group'] = guard.group
            persist(folder / 'offline_inference.json', report)
            print(f'Temporary Windows Firewall group: {guard.group}', flush=True)
            guard.install()
            result = 0 if verify(config, report, check_network=guard.state, firewall=True) else 2
        else:
            result = 0 if verify(config, report) else 2
    except KeyboardInterrupt:
        report['status'] = 'interrupted'
        result = 130
    except (OSError, RuntimeError, ValueError, KeyError, requests.RequestException, subprocess.TimeoutExpired) as exc:
        report.update(status='check_error', error_type=type(exc).__name__)
        print(f'Check stopped: {exc}', flush=True)
    finally:
        if guard and guard.install_started:
            try:
                guard.remove()
                report['firewall_cleanup'] = 'removed'
            except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
                report['firewall_cleanup'] = 'failed'
                report['firewall_cleanup_error'] = type(exc).__name__
                result = 2
                print(f'Cleanup failed. Remove the group {guard.group} from Administrator PowerShell.', flush=True)
        report['ended_utc'] = utc_now()
        persist(folder / 'offline_inference.json', report)
    print(f"Offline check status: {report['status']}")
    print(f"Evidence: {folder / 'offline_inference.json'}")
    return result


if __name__ == '__main__':
    raise SystemExit(main())
