"""Run a user-started local direct-task pilot against the three installed models."""

import argparse
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
import yaml

from pilot_power import record_window
from power_monitor import PowerMonitor
from score_receipt_pilot import score_run as score_receipts


ROOT = Path(__file__).resolve().parent.parent
CONTEXT = 8192
DEADLINE = 90
OUTPUT_LIMIT = 1024
THINK = False  # Ollama uses the lowest supported level if thinking cannot be disabled.
KEEP_ALIVE = '10m'


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def persist(path, record):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Windows can briefly deny a replacement while another process has the file open.
    for retry in range(5):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if retry == 4:
                raise
            time.sleep(0.05 * (retry + 1))


class LocalOllama:
    def __init__(self, host, session):
        address = urlsplit(host)
        if (address.scheme != 'http' or address.hostname not in ('localhost', '127.0.0.1', '::1')
                or address.path not in ('', '/') or address.query or address.fragment
                or address.username is not None):
            raise ValueError('The local pilot requires an HTTP loopback Ollama URL')
        self.host = host.rstrip('/')
        self.session = session
        self.session.trust_env = False

    def call(self, endpoint, body=None, timeout=10):
        with self.session.request('GET' if body is None else 'POST', self.host + endpoint,
                                  json=body, timeout=timeout, allow_redirects=False) as response:
            if response.status_code != 200:
                raise RuntimeError(f'Ollama {endpoint} returned HTTP {response.status_code}: {response.text[:400]}')
            return response.json()

    def run(self, model, prompt):
        return self.call('/api/generate', {
            'model': model, 'prompt': prompt, 'stream': False, 'keep_alive': KEEP_ALIVE, 'think': THINK,
            'options': {'num_ctx': CONTEXT, 'num_predict': OUTPUT_LIMIT},
        }, timeout=DEADLINE)

    def placement(self, model):
        loaded = self.call('/api/ps')['models']
        if len(loaded) != 1 or (loaded[0].get('model') or loaded[0].get('name')) != model:
            raise RuntimeError(f'Expected {model} to be the only loaded model')
        if loaded[0].get('context_length') != CONTEXT:
            raise RuntimeError(f'Ollama did not report {CONTEXT} context tokens for {model}')
        return loaded[0]

    def unload(self, model):
        self.call('/api/generate', {'model': model, 'stream': False, 'keep_alive': 0})


def attempt(ollama, model, task, repeat, origin, log):
    row = {'model': model, 'task_id': task['item_id'], 'repetition': repeat}
    row['started_utc'] = utc_now()
    started = time.monotonic() - origin
    row['started_elapsed_sec'] = started
    fatal = None
    try:
        raw = ollama.run(model, task['prompt'])
        if not isinstance(raw, dict):
            raise ValueError('Ollama response was not a JSON object')
        row['raw_response'] = raw
        if raw.get('done_reason') == 'length':
            row['status'] = 'output_limit'
        elif raw.get('done') is not True or not (raw.get('response') or '').strip():
            row['status'] = 'incomplete'
        elif not all(isinstance(raw.get(field), int) for field in ('prompt_eval_count', 'eval_count')):
            row['status'] = 'missing_native_token_counts'
        else:
            row['status'] = 'completed'
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        row['status'] = 'timeout' if isinstance(exc, requests.Timeout) else 'error'
        row['error'] = str(exc)
        fatal = exc
    finally:
        row.setdefault('status', 'interrupted')
        row['ended_elapsed_sec'] = time.monotonic() - origin
        row['duration_sec'] = row['ended_elapsed_sec'] - started
        log.write(json.dumps(row, ensure_ascii=False) + '\n')
        log.flush()
    if fatal:
        # A failed connection can leave inference in flight. Stop this pilot rather than overlap it.
        raise fatal
    return row['status']


def baseline_drift_reason(idle):
    thirds = idle['third_means_watts']
    if len(thirds) != 3 or any(watts is None for watts in thirds):
        return 'missing loaded-idle segment averages'
    spread = max(thirds) - min(thirds)
    limit = max(3.0, 0.05 * idle['mean_watts'])
    if spread > limit:
        return f'loaded-idle thirds differ by {spread:.1f} W (pilot limit {limit:.1f} W)'
    return None


def summarize(manifest, expected_attempts_per_block):
    blocks = manifest['blocks']
    manifest['attempted_count'] = sum(sum(block['attempt_status_counts'].values()) for block in blocks)
    manifest['completed_count'] = sum(block['attempt_status_counts'].get('completed', 0) for block in blocks)
    manifest['planned_attempt_count'] = len(blocks) * expected_attempts_per_block
    manifest['power_capture_status'] = ('recorded' if all(block['status'] == 'recorded' for block in blocks)
                                        else 'partial_power_coverage')
    manifest['loaded_idle_status'] = ('needs_review' if any(block['loaded_idle_drift_reason'] for block in blocks)
                                      else 'within_pilot_drift_limit')
    if manifest['completed_count'] != manifest['planned_attempt_count']:
        return 'incomplete_attempts'
    if manifest['power_capture_status'] != 'recorded':
        return 'partial_power_coverage'
    if manifest['loaded_idle_status'] == 'needs_review':
        return 'unstable_loaded_idle'
    return 'recorded'


def run_block(ollama, monitor, model, tasks, args, folder, block, checkpoint):
    block['status'] = 'loading'
    checkpoint()
    try:
        loaded = ollama.call('/api/generate', {
            'model': model, 'stream': False, 'keep_alive': KEEP_ALIVE,
            'options': {'num_ctx': CONTEXT, 'num_predict': OUTPUT_LIMIT},
        }, timeout=DEADLINE)
        if loaded.get('done') is not True:
            raise RuntimeError(f'Ollama did not complete the preload for {model}')
        block['placement_before_idle'] = ollama.placement(model)
        block['status'] = 'settling'
        checkpoint()
        print(f'{model}: settling for {args.settle_seconds}s, then recording loaded idle.', flush=True)
        time.sleep(args.settle_seconds)
        ollama.placement(model)
        block['status'] = 'loaded_idle'
        checkpoint()
        _, idle = record_window(monitor, folder / f"{block['id']}_idle.csv",
                                lambda _: time.sleep(args.baseline_seconds))
        block['loaded_idle'] = idle
        checkpoint()
        if idle['mean_watts'] is None:
            raise RuntimeError(f"{model} loaded idle is unavailable: {idle['energy_unavailable_reason']}")
        block['loaded_idle_drift_reason'] = baseline_drift_reason(idle)
        block['placement_before_work'] = ollama.placement(model)
        block['status'] = 'measuring'
        checkpoint()
        statuses = {}

        def workload(origin):
            with (folder / block['attempts_file']).open('x', encoding='utf-8') as log:
                for repeat in range(1, args.repetitions + 1):
                    for task in tasks:
                        status = attempt(ollama, model, task, repeat, origin, log)
                        statuses[status] = statuses.get(status, 0) + 1

        _, trace = record_window(monitor, folder / f"{block['id']}_work.csv", workload)
        block['workload'] = trace
        block['attempt_status_counts'] = statuses
        block['placement_after_work'] = ollama.placement(model)
        placements = [block[key] for key in ('placement_before_idle', 'placement_before_work', 'placement_after_work')]
        if len({placement.get('digest') for placement in placements}) != 1 or not placements[0].get('digest'):
            raise RuntimeError(f'Unable to confirm the same model revision throughout {model} block')
        gross = trace['gross_joules']
        block['incremental_batch_joules'] = None
        if gross is not None and block['loaded_idle_drift_reason'] is None:
            block['incremental_batch_joules'] = gross - idle['mean_watts'] * trace['duration_sec']
        block['status'] = 'recorded' if gross is not None else 'insufficient_power_coverage'
        checkpoint()
        print(f"{model}: power {block['status']}; attempts {statuses}.", flush=True)
        if block['loaded_idle_drift_reason']:
            print(f"  Loaded idle needs review: {block['loaded_idle_drift_reason']}", flush=True)
    finally:
        try:
            ollama.unload(model)
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            block['unload_error'] = str(exc)
        checkpoint()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--task', default='P-D02', help='Direct pilot task ID (default: P-D02)')
    selection.add_argument('--all-direct', action='store_true', help='Use all seven direct pilot tasks')
    selection.add_argument('--receipt-variants', action='store_true', help='Run the eight receipt variants and score raw JSON')
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--baseline-seconds', type=int, default=120)
    parser.add_argument('--settle-seconds', type=int, default=60, help='Wait after model load before capturing idle')
    args = parser.parse_args()
    if args.repetitions < 1 or args.baseline_seconds < 60:
        parser.error('Require at least one repetition and 60 seconds of loaded idle')
    if args.settle_seconds < 0 or args.settle_seconds + args.baseline_seconds > 540:
        parser.error('Require nonnegative settling and at most 540 seconds for settling plus idle capture')

    dataset_dir = ROOT / 'data' / ('receipt_variants_v1' if args.receipt_variants else 'pilot_v1')
    task_packet = (dataset_dir / 'tasks.json').read_bytes()
    dataset = json.loads(task_packet)
    tasks = [task for task in dataset['items'] if task['track'] == 'direct'
             and (args.all_direct or args.receipt_variants or task['item_id'] == args.task)]
    if not tasks:
        parser.error('Choose an item in the direct pilot track')
    scoring = None
    if args.receipt_variants:
        scoring_packet = (dataset_dir / 'scoring.json').read_bytes()
        scoring = json.loads(scoring_packet)
        task_ids = [task['item_id'] for task in tasks]
        if (scoring['dataset_version'] != dataset['dataset_version']
                or len(set(task_ids)) != len(task_ids)
                or set(task_ids) != set(scoring['expected_by_task'])):
            parser.error('The receipt scoring packet does not match the dataset')
    config = yaml.safe_load((ROOT / 'config.yaml').read_text(encoding='utf-8'))
    models = config['ollama']['models']
    if not models or len(set(models)) != len(models):
        parser.error('Set distinct local pilot model tags in config.yaml')
    monitor = PowerMonitor.from_config(config.get('shelly', {}))

    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    folder = ROOT / 'runs' / f'direct_pilot_{run_id}'
    folder.mkdir(parents=True)
    manifest = {
        'run_id': run_id, 'started_utc': utc_now(), 'status': 'started', 'mode': 'local_direct_pilot',
        'dataset_version': dataset['dataset_version'], 'task_packet_sha256': hashlib.sha256(task_packet).hexdigest(),
        'task_ids': [task['item_id'] for task in tasks], 'models': models, 'repetitions': args.repetitions,
        'context_tokens': CONTEXT, 'output_token_limit': OUTPUT_LIMIT, 'request_timeout_sec': DEADLINE,
        'think_requested': THINK, 'settle_sec': args.settle_seconds,
        'loaded_idle_sec': args.baseline_seconds, 'polling_interval_sec': monitor.polling_interval,
        'energy_scope': 'gross and loaded-idle-adjusted workload batch at the workstation wall',
        'blocks': [],
    }
    if scoring is not None:
        manifest['scoring_packet_sha256'] = hashlib.sha256(scoring_packet).hexdigest()

    def checkpoint():
        persist(folder / 'manifest.json', manifest)

    checkpoint()
    print(f'Pilot records: {folder}', flush=True)
    code = 0
    try:
        with requests.Session() as http:
            ollama = LocalOllama(config['ollama']['host'], http)
            manifest['ollama_version'] = ollama.call('/api/version').get('version')
            installed = {entry.get('model') or entry.get('name') for entry in ollama.call('/api/tags')['models']}
            missing = [model for model in models if model not in installed]
            if missing:
                raise RuntimeError('Missing local models: ' + ', '.join(missing))
            if ollama.call('/api/ps')['models']:
                raise RuntimeError('Unload currently running Ollama models before starting the pilot')
            for index, model in enumerate(models, 1):
                block = {'id': f'model_{index}', 'model': model, 'attempts_file': f'model_{index}_attempts.jsonl'}
                manifest['blocks'].append(block)
                run_block(ollama, monitor, model, tasks, args, folder, block, checkpoint)
                if block.get('unload_error') or ollama.call('/api/ps')['models']:
                    raise RuntimeError(f'Unable to verify all models unloaded after {model}')
        manifest['status'] = summarize(manifest, len(tasks) * args.repetitions)
        if manifest['status'] != 'recorded':
            code = 2
        print(f"Completed attempts: {manifest['completed_count']}/{manifest['planned_attempt_count']}", flush=True)
        if scoring is not None and manifest['attempted_count'] == manifest['planned_attempt_count']:
            try:
                scores = score_receipts(folder, manifest, scoring)
                scores_path = folder / 'receipt_scores.json'
                persist(scores_path, scores)
                print(f'Receipt scores: {scores_path}', flush=True)
                for result in scores['model_results']:
                    energy = result['gross_joules_per_valid_response']
                    label = f'{energy:.1f} J per valid response' if energy is not None else 'energy per valid response unavailable'
                    print(f"  {result['model']}: {result['passes']}/{result['attempts']} valid, {label}", flush=True)
            except (OSError, ValueError, KeyError) as exc:
                manifest['receipt_scoring_error'] = str(exc)
                print(f'Receipt scoring failed: {exc}', flush=True)
                code = 1
    except KeyboardInterrupt:
        manifest['status'] = 'interrupted'
        code = 130
    except (requests.RequestException, RuntimeError, KeyError, ValueError, OSError) as exc:
        manifest.update(status='aborted', error=str(exc))
        print(f'Pilot stopped: {exc}', flush=True)
        code = 1
    finally:
        manifest['ended_utc'] = utc_now()
        checkpoint()
        print(f"Pilot status: {manifest['status']}", flush=True)
    return code


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    raise SystemExit(main())
