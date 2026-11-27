"""Run the receipt or seven-task direct pilot once on each paid API, with Shelly monitoring."""

import argparse
import hashlib
import json
import os
import sqlite3
import time
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from dotenv import dotenv_values

from pilot_power import record_window
from power_monitor import PowerMonitor
from review_direct_pilot import load_direct_run, prepare_review
from run_direct_pilot import CONTEXT, DEADLINE, OUTPUT_LIMIT, ROOT, LocalOllama, baseline_drift_reason, persist, utc_now
from score_receipt_pilot import score_run


USD = 1_000_000  # The ledger stores integer microdollars.
IDLE_SECONDS = 120
SETTLE_SECONDS = 180
PRICING_CHECKED = '2026-11-25'
MAX_PROMPT_BYTES = 1024
# Leave ample room for provider formatting around one short text message.
INPUT_ALLOWANCE = CONTEXT - OUTPUT_LIMIT
# Conservative short-prompt, standard-tier rates in USD per million tokens, before credits.
PROVIDERS = {
    'openai': {
        'model': 'gpt-5.4-2026-03-05', 'url': 'https://api.openai.com/v1/responses',
        'key_env': 'OPENAI_API_KEY', 'budget_microdollars': 5 * USD, 'input_rate': 3, 'output_rate': 15,
        'pricing_url': 'https://developers.openai.com/api/docs/models/gpt-5.4',
        'settings': {'max_output_tokens': OUTPUT_LIMIT, 'reasoning': {'effort': 'low'},
                     'service_tier': 'default', 'store': False},
    },
    'gemini': {
        'model': 'gemini-4-neon',
        'url': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-4-neon:generateContent',
        'key_env': 'GEMINI_API_KEY', 'budget_microdollars': 10 * USD, 'input_rate': 3, 'output_rate': 15,
        'pricing_url': 'https://aistudio.google.com/docs/pricing#gemini-4-neon',
        'settings': {'maxOutputTokens': OUTPUT_LIMIT, 'thinkingConfig': {'thinkingLevel': 'LOW'}},
    },
}


def initialize_ledger(db):
    with db:
        db.execute('''CREATE TABLE IF NOT EXISTS cloud_requests (
            id INTEGER PRIMARY KEY, provider TEXT NOT NULL, run_id TEXT NOT NULL,
            task_id TEXT NOT NULL, reserved INTEGER NOT NULL, settled INTEGER,
            UNIQUE (provider, run_id, task_id)
        )''')


def reserve(db, provider, run_id, task_id, output_limit=OUTPUT_LIMIT):
    config = PROVIDERS[provider]
    maximum = (CONTEXT - output_limit) * config['input_rate'] + output_limit * config['output_rate']
    with db:
        db.execute('BEGIN IMMEDIATE')
        used, = db.execute('SELECT COALESCE(SUM(COALESCE(settled, reserved)), 0) FROM cloud_requests WHERE provider = ?',
                           (provider,)).fetchone()
        if used + maximum > config['budget_microdollars']:
            raise RuntimeError(f'{provider} has insufficient room in its budget for another request')
        return db.execute('INSERT INTO cloud_requests (provider, run_id, task_id, reserved) VALUES (?, ?, ?, ?)',
                          (provider, run_id, task_id, maximum)).lastrowid


def settle(db, reservation, provider, usage, output_limit=OUTPUT_LIMIT):
    config = PROVIDERS[provider]
    if provider == 'openai':
        input_tokens, total_tokens = usage['input_tokens'], usage['total_tokens']
    else:
        # Total minus prompt includes Gemini's separately billed thinking tokens.
        input_tokens, total_tokens = usage['promptTokenCount'], usage['totalTokenCount']
    if any(type(count) is not int or count < 0 for count in (input_tokens, total_tokens)):
        raise ValueError('Invalid token counts in paid response')
    output_tokens = total_tokens - input_tokens
    if input_tokens > CONTEXT - output_limit or not 0 <= output_tokens <= output_limit:
        raise ValueError('Paid response usage exceeds the reserved token limits')
    cost = input_tokens * config['input_rate'] + output_tokens * config['output_rate']
    with db:
        db.execute('UPDATE cloud_requests SET settled = ? WHERE id = ?', (cost, reservation))
    return cost


def request_answer(http, provider, key, prompt, row, output_limit=OUTPUT_LIMIT, timeout=DEADLINE, schema=None):
    config = PROVIDERS[provider]
    if provider == 'openai':
        headers = {'Authorization': f'Bearer {key}'}
        body = {'model': config['model'], 'input': prompt, **config['settings'], 'max_output_tokens': output_limit}
        if schema is not None:
            body['text'] = {'format': {'type': 'json_schema', 'name': 'agent_action', 'strict': True, 'schema': schema}}
    else:
        headers = {'x-goog-api-key': key}
        body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                'generationConfig': {**config['settings'], 'maxOutputTokens': output_limit}}
        if schema is not None:
            body['generationConfig'].update(responseMimeType='application/json', responseJsonSchema=schema)
    try:
        with http.post(config['url'], headers=headers, json=body, timeout=timeout, allow_redirects=False) as response:
            row['request_id'] = response.headers.get('x-request-id')
            if response.status_code != 200:
                raise RuntimeError(f'{provider} returned HTTP {response.status_code}, request ID {row["request_id"]}')
            payload = response.json()
    except requests.RequestException as exc:
        # Transport exceptions may include headers or response content.
        raise RuntimeError(f'{provider} request failed ({type(exc).__name__})') from None

    if provider == 'openai':
        row['returned_model'] = payload['model']
        row['usage'] = payload['usage']
        row['service_tier'] = payload.get('service_tier')
        if row['service_tier'] not in (None, 'default'):
            raise ValueError('OpenAI reported an unexpected billing tier')
        parts = [part for message in payload['output'] if message['type'] == 'message'
                 for part in message['content']]
        reason = (payload.get('incomplete_details') or {}).get('reason', payload['status'])
        completed = payload['status'] == 'completed' and not any(part['type'] == 'refusal' for part in parts)
        answer = ''.join(part['text'] for part in parts if part['type'] == 'output_text')
    else:
        row['request_id'] = payload.get('responseId') or row['request_id']
        row['returned_model'] = payload.get('modelVersion')
        row['usage'] = payload['usageMetadata']
        row['service_tier'] = row['usage'].get('serviceTier')
        tier = row['service_tier']
        if tier is not None and tier.lower().removeprefix('service_tier_') not in ('standard', 'unspecified'):
            raise ValueError('Gemini reported an unexpected billing tier')
        candidate = next(iter(payload.get('candidates', [])), {})
        parts = (candidate.get('content') or {}).get('parts', [])
        reason = candidate.get('finishReason') or (payload.get('promptFeedback') or {}).get('blockReason')
        completed = reason == 'STOP'
        answer = ''.join(part.get('text', '') for part in parts if not part.get('thought'))
    row['raw_response'] = {'response': answer, 'finish_reason': reason}
    if reason in ('max_output_tokens', 'MAX_TOKENS'):
        return 'output_limit'
    if not completed or not answer.strip():
        return 'incomplete'
    return 'completed'


def run_block(http, db, monitor, provider, key, tasks, folder, manifest, block):
    print(f'{provider}: recording {IDLE_SECONDS}s of workstation idle.', flush=True)
    _, idle = record_window(monitor, folder / f'{provider}_idle.csv', lambda _: time.sleep(IDLE_SECONDS))
    block['workstation_idle'] = idle
    if idle['mean_watts'] is None:
        raise RuntimeError(f'{provider} idle trace unavailable: {idle["energy_unavailable_reason"]}')
    drift = baseline_drift_reason(idle)
    block['workstation_idle_drift_reason'] = drift.replace('loaded-idle', 'workstation idle') if drift else None
    if drift:
        print(f"  {block['workstation_idle_drift_reason']}", flush=True)
    statuses = Counter()
    block['attempt_status_counts'] = statuses
    print(f'{provider}: sending {len(tasks)} measured requests.', flush=True)

    def workload(origin):
        with (folder / block['attempts_file']).open('x', encoding='utf-8') as log:
            for task in tasks:
                task_id = task['item_id']
                try:
                    reservation = reserve(db, provider, manifest['run_id'], task_id)
                except (RuntimeError, sqlite3.Error) as exc:
                    return str(exc)
                row = {'model': block['model'], 'task_id': task_id, 'repetition': 1,
                       'started_utc': utc_now(), 'started_elapsed_sec': time.monotonic() - origin,
                       'budget_reservation_id': reservation, 'status': 'interrupted'}
                try:
                    status = request_answer(http, provider, key, task['prompt'], row)
                    row['budget_usage_microdollars'] = settle(db, reservation, provider, row['usage'])
                    row['status'] = status
                except (ValueError, KeyError, TypeError, AttributeError, RuntimeError, sqlite3.Error) as exc:
                    row.update(status='error', error=str(exc))
                    return f'{provider} {task_id}: {exc}. Budget reservation retained.'
                finally:
                    row['ended_elapsed_sec'] = time.monotonic() - origin
                    row['duration_sec'] = row['ended_elapsed_sec'] - row['started_elapsed_sec']
                    statuses[row['status']] += 1
                    log.write(json.dumps(row, ensure_ascii=False) + '\n')
                    log.flush()
        return None

    error, trace = record_window(monitor, folder / f'{provider}_work.csv', workload)
    block['workload'] = trace
    gross = trace['gross_joules']
    block['incremental_batch_joules'] = (gross - idle['mean_watts'] * trace['duration_sec']
                                         if gross is not None and drift is None else None)
    if gross is None:
        print(f"  {provider} workload energy unavailable: {trace['energy_unavailable_reason']}", flush=True)
    if error:
        raise RuntimeError(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Start paid API requests and workstation measurement')
    parser.add_argument('--all-direct', action='store_true', help='Run the seven original direct tasks')
    parser.add_argument('--local-run', type=Path, help='Saved local all-direct run to pair with --all-direct')
    args = parser.parse_args()
    if not args.execute:
        parser.error('Use --execute when ready to start the paid pilot')
    if args.all_direct != (args.local_run is not None):
        parser.error('Use --all-direct and --local-run together')

    dotenv = dotenv_values(ROOT / '.env')
    keys = {}
    for provider, settings in PROVIDERS.items():
        name = settings['key_env']
        key = (os.getenv(name) or dotenv.get(name) or '').strip()
        if not key or 'your-' in key:
            parser.error(f'Set {name} in the repository .env file or environment')
        keys[provider] = key

    packet = ROOT / 'data' / ('pilot_v1' if args.all_direct else 'receipt_variants_v1')
    task_bytes = (packet / 'tasks.json').read_bytes()
    score_bytes = (packet / 'scoring.json').read_bytes()
    dataset, scoring = json.loads(task_bytes), json.loads(score_bytes)
    tasks = [task for task in dataset['items'] if task['track'] == 'direct']
    task_ids = [task['item_id'] for task in tasks]
    score_by_task = scoring['criteria'] if args.all_direct else scoring['expected_by_task']
    expected_ids = {f'P-D{index:02}' for index in range(1, 8)} if args.all_direct else set(score_by_task)
    expected_count = 7 if args.all_direct else 8
    if (len(task_ids) != expected_count or set(task_ids) != expected_ids or len(expected_ids) != expected_count
            or not expected_ids <= score_by_task.keys() or dataset['dataset_version'] != scoring['dataset_version']):
        parser.error('The direct tasks and scoring packet do not match')
    if any(len(task['prompt'].encode('utf-8')) > MAX_PROMPT_BYTES for task in tasks):
        parser.error(f'The pilot limits each text prompt to {MAX_PROMPT_BYTES} UTF-8 bytes')
    config = yaml.safe_load((ROOT / 'config.yaml').read_text(encoding='utf-8'))
    task_hash = hashlib.sha256(task_bytes).hexdigest()
    local_run = None
    if args.all_direct:
        try:
            local_run = load_direct_run(args.local_run, dataset['dataset_version'], task_hash, task_ids,
                                        config['ollama']['models'])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            parser.error(f'Unable to use that saved local run: {exc}')
    monitor = PowerMonitor.from_config(config['shelly'])

    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    mode = 'cloud_direct_pilot' if args.all_direct else 'cloud_receipt_pilot'
    folder = ROOT / 'runs' / f'{mode}_{run_id}'
    folder.mkdir(parents=True)
    manifest = {
        'run_id': run_id, 'started_utc': utc_now(), 'status': 'started', 'mode': mode,
        'dataset_version': dataset['dataset_version'], 'task_packet_sha256': task_hash,
        'scoring_packet_sha256': hashlib.sha256(score_bytes).hexdigest(), 'task_ids': task_ids, 'repetitions': 1,
        'output_token_limit': OUTPUT_LIMIT, 'request_timeout_sec': DEADLINE, 'settle_sec': SETTLE_SECONDS,
        'workstation_idle_sec': IDLE_SECONDS, 'polling_interval_sec': monitor.polling_interval,
        'energy_scope': 'client workstation wall only', 'pricing_checked': PRICING_CHECKED,
        'input_token_allowance': INPUT_ALLOWANCE, 'max_prompt_bytes': MAX_PROMPT_BYTES,
        'credit_policy': 'standard rates before credits and data-sharing discounts',
        'openai_data_sharing': 'enabled as reported by researcher; verify the key project in the dashboard',
        'providers': PROVIDERS, 'blocks': [],
    }
    if local_run:
        manifest['paired_local_run_id'] = local_run[0]['run_id']
    manifest_path = folder / 'manifest.json'
    persist(manifest_path, manifest)
    print(f'Pilot records: {folder}', flush=True)
    code = 0
    try:
        with closing(sqlite3.connect(folder.parent / 'cloud_budget.sqlite3')) as db, requests.Session() as local:
            initialize_ledger(db)
            ollama = LocalOllama(config['ollama']['host'], local)
            if ollama.call('/api/ps')['models']:
                raise RuntimeError('Unload currently running Ollama models before starting the pilot')
            print(f'Waiting {SETTLE_SECONDS}s for the workstation to settle.', flush=True)
            time.sleep(SETTLE_SECONDS)
            for provider, settings in PROVIDERS.items():
                if ollama.call('/api/ps')['models']:
                    raise RuntimeError('An Ollama model is running. Stop local generation before the cloud pilot.')
                block = {'provider': provider, 'model': settings['model'], 'attempts_file': f'{provider}_attempts.jsonl'}
                manifest['blocks'].append(block)
                with requests.Session() as http:
                    run_block(http, db, monitor, provider, keys[provider], tasks, folder, manifest, block)
                persist(manifest_path, manifest)
        blocks = manifest['blocks']
        if any(block['workload']['gross_joules'] is None for block in blocks):
            manifest['status'] = 'partial_power_coverage'
        elif any(block['workstation_idle_drift_reason'] for block in blocks):
            manifest['status'] = 'unstable_workstation_idle'
        else:
            manifest['status'] = 'recorded'
        code = 0 if manifest['status'] == 'recorded' else 2
        if local_run:
            pending = prepare_review(folder, manifest, tasks, scoring, local_run)
            print(f'Direct comparison: {folder / "direct_comparison.json"}', flush=True)
            print(f'Blind review: {folder / "review_packet.md"} ({pending} responses to grade)', flush=True)
        else:
            scores = score_run(folder, manifest, scoring)
            scores['energy_scope'] = manifest['energy_scope']
            output = folder / 'receipt_scores.json'
            persist(output, scores)
            print(f'Receipt scores: {output}', flush=True)
            for result in scores['model_results']:
                print(f"  {result['model']}: {result['passes']}/{result['attempts']} strict passes", flush=True)
    except KeyboardInterrupt:
        manifest['status'] = 'interrupted'
        code = 130
    except (requests.RequestException, RuntimeError, ValueError, OSError, KeyError, sqlite3.Error) as exc:
        manifest.update(status='aborted', error=str(exc))
        print(f'Pilot stopped: {exc}', flush=True)
        code = 1
    finally:
        manifest['ended_utc'] = utc_now()
        persist(manifest_path, manifest)
        print(f"Pilot status: {manifest['status']}", flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
