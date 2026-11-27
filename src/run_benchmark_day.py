"""Run the authored benchmark sections unattended and save a reviewable report."""

import argparse
import hashlib
import json
import os
import random
import sqlite3
import subprocess
import time
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from dotenv import dotenv_values

import run_agent_pilot as agent
import run_cloud_receipt_pilot as cloud
import run_direct_pilot as local
from agent_worker import Worker
from power_monitor import PowerMonitor
from review_direct_pilot import prepare_review, read_attempts, write_comparison
from score_receipt_pilot import score_run


SECTIONS = ('calibration', 'direct', 'receipts', 'agent')
AGENT_PROTOCOL = 'structured-one-action-v3'
SEED = 20261126
SETTLE = 180
CALIBRATION = {'item_id': 'CAL-01', 'prompt': 'Read increment.py. Fix increment(n) to add one to n. '
              'Leave the existing test unchanged. Run the test tool and finish with a short summary.',
              'workspace_files': {'increment.py': 'def increment(n):\n    return n\n',
                                  'test_increment.py': 'import unittest\nfrom increment import increment\n'
                                  'class IncrementTests(unittest.TestCase):\n'
                                  '    def test_increment(self):\n        self.assertEqual(increment(5), 6)\n'}}
RECOVERABLE = (OSError, RuntimeError, ValueError, KeyError, TypeError, requests.RequestException,
               sqlite3.Error, subprocess.TimeoutExpired)


def read(path):
    return json.loads(path.read_bytes())


def suites():
    root = local.ROOT / 'data'
    original = read(root / 'pilot_v1' / 'tasks.json')
    original_scores = read(root / 'pilot_v1' / 'scoring.json')
    extension = read(root / 'benchmark_day_v1.json')
    tasks = [task for task in original['items'] if task['track'] == 'direct'] + extension['items']
    criteria = dict(original_scores['criteria'])
    criteria.update((task['item_id'], {key: task[key] for key in ('required', 'automatic_failure', 'verification')
                                       if key in task}) for task in extension['items'])
    receipt_tasks = read(root / 'receipt_variants_v1' / 'tasks.json')
    receipt_scores = read(root / 'receipt_variants_v1' / 'scoring.json')
    agent_tasks, agent_scores, _ = agent.packet()

    def suite(version, items, scoring):
        ids = [task['item_id'] for task in items]
        if len(set(ids)) != len(ids):
            raise ValueError(f'Duplicate task IDs in {version}')
        digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
        return {'tasks': items, 'scoring': scoring, 'task_ids': ids, 'dataset_version': version,
                'task_packet_sha256': digest(items), 'scoring_packet_sha256': digest(scoring)}

    for task in tasks + receipt_tasks['items']:
        if len(task['prompt'].encode('utf-8')) > cloud.MAX_PROMPT_BYTES:
            raise ValueError(f'Direct input too large for {task["item_id"]}')
    result = {
        'calibration': suite('agent-calibration-v1', [CALIBRATION], {}),
        'direct': suite(extension['dataset_version'], tasks, {'criteria': criteria, 'scorer_version': 'direct-rubric-v1'}),
        'receipts': suite(receipt_tasks['dataset_version'], receipt_tasks['items'], receipt_scores),
        'agent': suite('agent-structured-v2', agent_tasks, agent_scores),
    }
    if set(result['receipts']['task_ids']) != receipt_scores['expected_by_task'].keys():
        raise ValueError('Receipt prompts do not match their scoring packet')
    return result


def gemini_recovery(source, packets):
    manifest = read(source / 'manifest.json')
    baseline = packets['direct']
    if manifest['fingerprints']['direct'] != [baseline['task_packet_sha256'], baseline['scoring_packet_sha256']]:
        raise ValueError('The original campaign does not use the current direct-task packet')
    block, = [record for record in manifest['sections']['direct'] if record['provider'] == 'gemini']
    receipt, = [record for record in manifest['sections']['receipts'] if record['provider'] == 'gemini']
    if block['status'] != 'failed' or receipt['status'] != 'skipped':
        raise ValueError('Expected a failed Gemini direct block and a skipped receipt block')
    with (source / 'direct' / block['block']['attempts_file']).open(encoding='utf-8') as log:
        rows = [json.loads(line) for line in log]
    attempted = {row['task_id'] for row in rows}
    if len(attempted) != len(rows) or not attempted <= set(baseline['task_ids']):
        raise ValueError('The saved Gemini attempt log has invalid task IDs')
    # Errors remain in the source campaign. An ambiguous request may already have been charged.
    tasks = [task for task in baseline['tasks'] if task['item_id'] not in attempted]
    if not tasks:
        raise ValueError('The Gemini direct block has no undispatched tasks to recover')
    direct = task_subset(baseline, tasks)
    return {'direct': direct, 'receipts': packets['receipts']}, {
        'source_run': source.name, 'prior_attempts': len(rows),
        'ambiguous_task_ids': [row['task_id'] for row in rows if row['status'] == 'error'],
    }


def task_subset(suite, tasks):
    digest = hashlib.sha256(json.dumps(tasks, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    return {**suite, 'tasks': tasks, 'task_ids': [task['item_id'] for task in tasks], 'task_packet_sha256': digest}


def repeat_panel(packets):
    direct = packets['direct']
    by_domain = {}
    for task in sorted(direct['tasks'], key=lambda row: row['item_id']):
        by_domain.setdefault(task['domain'], []).append(task)
    selection = [task for domain, tasks in sorted(by_domain.items())
                 for task in random.Random(f'paired-repeat-v1/{SEED}/{domain}').sample(tasks, 2)]
    return {'direct': task_subset(direct, selection), 'receipts': packets['receipts']}


@contextmanager
def meter_lock():
    path = local.ROOT / 'runs' / '.benchmark-day.lock'
    path.parent.mkdir(exist_ok=True)
    with path.open('a+b') as lock:
        if not lock.tell():
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError('Another benchmark-day process owns the Shelly measurement window') from None
        yield


@contextmanager
def loaded(ollama, model):
    if ollama.call('/api/ps')['models']:
        raise RuntimeError('Unload active Ollama models before starting the next benchmark block')
    try:
        response = ollama.call('/api/generate', {'model': model, 'stream': False, 'keep_alive': local.KEEP_ALIVE,
                                               'options': agent.OPTIONS}, timeout=local.DEADLINE)
        if not response.get('done'):
            raise RuntimeError('Local model did not preload')
        yield ollama.placement(model)
    finally:
        ollama.unload(model)


def run_step(step, section, tasks, worker, monitor, folder, ollama, http, db, keys, manifest, checkpoint):
    model = step['model']
    provider = step['provider']
    if ollama.call('/api/ps')['models']:
        raise RuntimeError('Unload active Ollama models before measuring')
    if section in ('direct', 'receipts'):
        step['attempts_file'] = f"{step['id']}_attempts.jsonl" if provider == 'local' else f'{provider}_attempts.jsonl'
        if provider == 'local':
            args = argparse.Namespace(repetitions=1, settle_seconds=SETTLE, baseline_seconds=120)
            # The local runner uses its own status during collection.
            block = {**step}
            step['block'] = block
            local.run_block(ollama, monitor, model, tasks, args, folder, block, checkpoint)
            if block.get('unload_error'):
                raise RuntimeError('Unable to confirm the local model unloaded')
            return
        print(f'{model}: settling for {SETTLE}s before measuring {section}.', flush=True)
        time.sleep(SETTLE)
        block = dict(step)
        step['block'] = block
        cloud.run_block(http, db, monitor, provider, keys[provider], tasks, folder, manifest, block)
        return

    def run_tools(generate):
        if section == 'calibration':
            filename = folder / f"{step['id']}_CAL-01.json"
            agent.run_attempt(worker, CALIBRATION, generate, model, filename, time.monotonic(), True, 7)
            row = read(filename)
            actions = {turn.get('action') for turn in row['turns']}
            if (row['status'] == 'finished' and row['public_verified'] and 'read increment.py' in actions
                    and 'write increment.py' in actions
                    and row['files'].get('test_increment.py') == CALIBRATION['workspace_files']['test_increment.py']):
                check = worker.run(row['files'], ['-c', 'from increment import increment\n'
                                                   'assert [increment(i) for i in (-4, 0, 8)] == [-3, 1, 9]'])
                step['interface_passed'] = check['exit_code'] == 0
            else:
                step['interface_passed'] = False
            step['attempt_file'] = filename.name
        else:
            block = dict(step)
            step['block'] = block
            agent.measure_block(worker, monitor, folder, block, tasks, generate, structured=True)

    if provider == 'local':
        with loaded(ollama, model) as placement:
            step['placement'] = placement
            run_tools(agent.local_generate(ollama, model, structured=True))
            after = ollama.placement(model)
            if not placement.get('digest') or placement['digest'] != after.get('digest'):
                raise RuntimeError('Local model revision changed during the block')
    else:
        run_tools(agent.cloud_generate(http, db, provider, keys[provider], manifest['run_id'], structured=True))


def section_manifest(manifest, suites_by_name, name):
    suite = suites_by_name[name]
    steps = manifest['sections'][name]
    return {**{field: suite[field] for field in ('dataset_version', 'task_packet_sha256', 'scoring_packet_sha256', 'task_ids')},
            'run_id': manifest['run_id'], 'status': 'recorded' if all(s['status']=='recorded' for s in steps) else 'partial',
            'energy_scope': 'workstation wall; cloud electricity covers the client and local tools', 'repetitions': 1,
            'worker_image_id': manifest['worker_image_id'], 'blocks': [s['block'] for s in steps if s['status']=='recorded']}


def grade_sections(folder, manifest, packets, worker):
    for name in ('direct', 'receipts', 'agent'):
        if name not in packets:
            continue
        target = folder / name
        suite = packets[name]
        section = section_manifest(manifest, packets, name)
        if not section['blocks']:
            continue
        try:
            if name == 'direct' and not (target / 'review_key.json').exists():
                by_condition = {condition: {**section, 'energy_scope': (
                    'client workstation wall only' if condition == 'cloud' else 'workstation wall during local inference'),
                    'blocks': [b for b in section['blocks'] if b['condition'] == condition]}
                                for condition in ('local', 'cloud')}
                local_section = by_condition['local']
                prepare_review(target, by_condition['cloud'], suite['tasks'], suite['scoring'],
                               (local_section, read_attempts(target, local_section)))
            if name == 'receipts':
                scores = score_run(target, section, suite['scoring'])
                scores['energy_scope'] = section['energy_scope']
                local.persist(target / 'receipt_scores.json', scores)
            if name == 'agent' and not (target / 'agent_scores.json').exists():
                agent.grade_run(worker, target, section, suite['tasks'], suite['scoring'])
        except RECOVERABLE as exc:
            manifest['grading_errors'][name] = str(exc)
        else:
            manifest['grading_errors'].pop(name, None)


def write_report(folder, manifest):
    lines = ['# Unattended benchmark results', '', f"Run ID `{manifest['run_id']}`", '',
             f"Campaign status **{manifest['status']}**", '',
             'Energy is measured at the workstation wall. Cloud-server energy requires separate evidence.',
             'Privacy policy review and provider billing reconciliation are documented separately.', '']
    if recovery := manifest.get('recovery'):
        source = recovery['source_run']
        lines.extend([f'Gemini follow-up to [{source}](../{source}/benchmark_report.md).',
                      f"Preserved {recovery['prior_attempts']} original attempt records, including any timeout. "
                      'Follow-up power traces have their own baseline and measurement window.', ''])
    output = {'calibration': None, 'direct': 'direct_comparison.json',
              'receipts': 'receipt_scores.json', 'agent': 'agent_scores.json'}
    names = {'calibration': 'Agent interface calibration', 'direct': 'Direct tasks by category',
             'receipts': 'Strict JSON receipt extraction', 'agent': 'Agentic Python tasks'}
    for name, steps in manifest['sections'].items():
        target = folder / name
        lines.extend([f'## {names[name]}', '', '| Model | Block status | Detail |', '| --- | --- | --- |'])
        for step in steps:
            detail = step.get('reason', '')
            block = step.get('block', {})
            if name == 'calibration' and step['status'] == 'recorded':
                detail = 'Tool interface passed' if step['interface_passed'] else 'Tool interface did not pass'
            elif step['status'] == 'recorded':
                work = block['workload']
                gross = work['gross_joules']
                detail = f'Gross {gross:,.0f} J' if gross is not None else 'Power coverage incomplete'
                adjusted = block.get('idle_adjusted_joules', block.get('incremental_batch_joules'))
                detail += f'; adjusted {adjusted:,.0f} J' if adjusted is not None else '; adjusted unavailable'
                counts = block.get('statuses', block.get('attempt_status_counts', {}))
                if counts:
                    detail += '; ' + ', '.join(f'{count} {status}' for status, count in counts.items())
            lines.append(f"| {step['model']} | {step['status']} | {detail.replace('|', '/').replace(chr(10), ' ')[:250]} |")
        lines.append('')
        filename = output[name]
        if filename and (target / filename).is_file():
            report = read(target / filename)
            if name == 'direct':
                lines.extend(['| Category | Model | Adequate | Inadequate | Pending | Mean seconds |',
                              '| --- | --- | ---: | ---: | ---: | ---: |'])
                for category in dict.fromkeys(report['tasks'].values()):
                    for model in report['models']:
                        items = [a for a in model['by_task'].values() if a['category'] == category]
                        counts = [sum(a[field] for a in items) for field in ('adequate', 'inadequate', 'pending')]
                        duration = sum(a['mean_sec'] for a in items) / len(items)
                        label = category.replace('_', ' ')
                        lines.append(f"| {label} | {model['model']} | {counts[0]} | {counts[1]} | {counts[2]} | {duration:.2f} |")
                lines.append('')
            elif name == 'receipts':
                lines.extend(['| Model | Strict passes | Mean seconds | Gross J per pass | Failed receipt IDs |',
                              '| --- | ---: | ---: | ---: | --- |'])
                for model in report['model_results']:
                    failed = ', '.join(a['task_id'] for a in model['attempt_scores'] if not a['pass']) or '—'
                    energy = model['gross_joules_per_valid_response']
                    j = f'{energy:,.0f}' if energy is not None else '—'
                    lines.append(f"| {model['model']} | {model['passes']}/{model['attempts']} | {model['mean_response_sec']:.2f} | {j} | {failed} |")
                lines.append('')
            else:
                lines.extend(['| Model | Task | Grade | Seconds | Failed or pending checks |', '| --- | --- | --- | ---: | --- |'])
                for model in report['models']:
                    for row in model['attempts']:
                        checks = ', '.join(key for key, value in row['checks'].items() if value is not True) or '—'
                        lines.append(f"| {model['model']} | {row['task_id']} | {row['grade']} | {row['duration_sec']:.1f} | {checks} |")
                lines.append('')
            lines.append(f'[Scores and task breakdown]({name}/{filename})')
            if (target / 'review_packet.md').is_file():
                lines.append(f' · [Blind review packet]({name}/review_packet.md)')
            if (target / 'refactor_review.md').is_file():
                lines.append(f' · [Blind refactor review]({name}/refactor_review.md)')
            lines.append('')
        if name in manifest['grading_errors']:
            lines.extend([f"Grading needs review. {manifest['grading_errors'][name]}", ''])
        lines.extend([f'Raw logs and traces are in `{name}/`.', ''])
    lines.extend(['## API budget ledger', '', 'Conservative usage estimates before credits and discounts.', '',
                  '| Provider | Requests reserved | Settled estimate | Unsettled reservation |',
                  '| --- | ---: | ---: | ---: |'])
    for provider, count, settled, held in manifest.get('budget', []):
        lines.append(f'| {provider} | {count} | ${settled / cloud.USD:.4f} | ${held / cloud.USD:.4f} |')
    lines.extend(['', '## Remaining research evidence', '',
                  '- Verify the project settings and reconcile actual costs and credits in each provider dashboard.',
                  '- Compare documented privacy settings with observed data flows in the separate privacy protocol.',
                  '- Review cloud-server energy sources separately from the Shelly trace.',
                  '- Use this pass to select follow-up repetitions and record training experiments separately.', ''])
    (folder / 'benchmark_report.md').write_text('\n'.join(lines), encoding='utf-8')


def refresh(folder):
    manifest = read(folder / 'manifest.json')
    direct_folder = folder / 'direct'
    if (direct_folder / 'review_key.json').is_file():
        write_comparison(direct_folder)
    agent_folder = folder / 'agent'
    review_path = agent_folder / 'refactor_review.json'
    scores_path = agent_folder / 'agent_scores.json'
    if review_path.is_file() and scores_path.is_file():
        grades = read(review_path)
        scores = read(scores_path)
        reviews = {answer['review_id']: answer for model in scores['models']
                   for answer in model['attempts'] if 'review_id' in answer}
        fields = {'explains_order', 'shared_channel_loop'}
        if (not isinstance(grades, dict) or grades.keys() != reviews.keys()
                or any(not isinstance(item, dict) or item.keys() != fields
                       or any(value is not None and type(value) is not bool for value in item.values())
                       for item in grades.values())):
            raise ValueError('Keep the original refactor review IDs and use true, false, or null')
        for answer_id, answer in reviews.items():
            checks = grades[answer_id]
            answer['checks'].update(checks)
            answer['grade'] = ('review_required' if None in checks.values() else
                               'adequate' if all(checks.values()) else 'inadequate')
        for model in scores['models']:
            labels = [answer['grade'] for answer in model['attempts']]
            model['grades'] = {label: labels.count(label) for label in dict.fromkeys(labels)}
            adequate = labels.count('adequate')
            for metric in ('gross', 'idle_adjusted'):
                energy = model[f'{metric}_batch_joules']
                model[f'{metric}_joules_per_adequate'] = (energy / adequate if energy is not None and adequate
                                                          and 'review_required' not in labels else None)
        local.persist(scores_path, scores)
    write_report(folder, manifest)


def execute(folder, packets, config, keys, worker, resume, recovery=None):
    path = folder / 'manifest.json'
    conditions = [] if recovery else [('local', name) for name in config['ollama']['models']]
    conditions.extend((name, cloud.PROVIDERS[name]['model']) for name in keys)
    random.Random(SEED).shuffle(conditions)
    fingerprints = {name: [s['task_packet_sha256'], s['scoring_packet_sha256']] for name, s in packets.items()}
    if resume:
        manifest = read(path)
        if (manifest['fingerprints'] != fingerprints or manifest['worker_image_id'] != (worker.image if worker else None)
                or manifest['conditions'] != [list(pair) for pair in conditions]
                or manifest.get('recovery') != recovery or manifest['agent_protocol'] != AGENT_PROTOCOL):
            raise ValueError('The saved campaign uses a different dataset, model list, protocol, or worker image')
    else:
        folder.mkdir(parents=True)
        manifest = {'run_id': folder.name, 'status': 'running', 'seed': SEED, 'conditions': conditions,
                    'started_utc': local.utc_now(), 'direct_output_limit': local.OUTPUT_LIMIT,
                    'agent_output_limit': agent.OUTPUT_LIMIT, 'context_tokens': local.CONTEXT,
                    'agent_turn_limit': agent.TURN_LIMIT, 'agent_task_seconds': agent.TASK_SECONDS,
                    'settle_seconds': SETTLE, 'idle_seconds': 120, 'cloud_pricing_checked': cloud.PRICING_CHECKED,
                    'openai_data_sharing': 'enabled as reported by the researcher; verify the key project in the dashboard',
                    'agent_protocol': AGENT_PROTOCOL, 'worker_image_id': worker.image if worker else None,
                    'recovery': recovery, 'fingerprints': fingerprints,
                    'grading_errors': {}, 'sections': {name: [{'id': f'block_{index}', 'model': model, 'provider': provider,
                       'condition': 'local' if provider == 'local' else 'cloud', 'status': 'pending'}
                       for index, (provider, model) in enumerate(conditions, 1)] for name in packets}}
        for name in packets:
            (folder / name).mkdir()

    def checkpoint():
        local.persist(path, manifest)

    manifest['status'] = 'running'
    checkpoint()
    write_report(folder, manifest)
    try:
        monitor = PowerMonitor.from_config(config['shelly'])
        with closing(sqlite3.connect(folder.parent / 'cloud_budget.sqlite3')) as db, requests.Session() as session:
            cloud.initialize_ledger(db)
            ollama = local.LocalOllama(config['ollama']['host'], session)
            installed = {model.get('model') or model.get('name') for model in ollama.call('/api/tags')['models']}
            manifest['ollama_version'] = ollama.call('/api/version').get('version')
            if ollama.call('/api/ps')['models']:
                raise RuntimeError('Unload running Ollama models before starting the campaign')
            if not monitor.test_connection():
                raise RuntimeError('Shelly did not return a power reading')

            disabled = set()
            for name in packets:
                tasks = list(packets[name]['tasks'])
                if name != 'calibration':
                    random.Random(f'{SEED}/{name}').shuffle(tasks)
                for index, step in enumerate(manifest['sections'][name]):
                    provider = step['provider']
                    if step['status'] in ('running', 'failed', 'interrupted') and provider != 'local':
                        disabled.add(provider)
                    if step['status'] == 'running':
                        step.update(status='interrupted', reason='Partial files preserved; block was not replayed')
                    if step['status'] != 'pending':
                        continue
                    if name == 'agent' and not manifest['sections']['calibration'][index].get('interface_passed'):
                        step.update(status='skipped', reason='Agent interface did not pass calibration')
                    elif provider in disabled:
                        step.update(status='skipped', reason='Provider stopped after an ambiguous or failed block')
                    elif provider == 'local' and step['model'] not in installed:
                        step.update(status='skipped', reason='This Ollama model is not installed')
                    else:
                        step['status'] = 'running'
                        checkpoint()
                        print(f"{name} / {step['model']}", flush=True)
                        try:
                            with requests.Session() as http:
                                run_step(step, name, tasks, worker, monitor, folder / name, ollama, http, db, keys,
                                         manifest, checkpoint)
                        except RECOVERABLE as exc:
                            step.update(status='failed', reason=str(exc))
                            if provider != 'local':
                                disabled.add(provider)
                            print(f'  Block stopped: {exc}', flush=True)
                        else:
                            step['status'] = 'recorded'
                    checkpoint()
                    write_report(folder, manifest)
            manifest['budget'] = db.execute('''SELECT provider, count(*), COALESCE(SUM(settled), 0),
                        COALESCE(SUM(CASE WHEN settled IS NULL THEN reserved ELSE 0 END), 0)
                        FROM cloud_requests WHERE run_id = ? GROUP BY provider''', (manifest['run_id'],)).fetchall()
        grade_sections(folder, manifest, packets, worker)
        steps = [step for group in manifest['sections'].values() for step in group]
        complete = (all(step['status'] == 'recorded' for step in steps) and not manifest['grading_errors']
                    and all(step['block'].get('idle_adjusted_joules', step['block'].get('incremental_batch_joules'))
                            is not None for step in steps if 'block' in step))
        manifest['status'] = 'complete' if complete else 'complete_with_flags'
    except BaseException:
        manifest['status'] = 'interrupted'
        raise
    finally:
        manifest['last_checkpoint_utc'] = local.utc_now()
        checkpoint()
        write_report(folder, manifest)
    return manifest['status']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', action='store_true')
    mode.add_argument('--execute', action='store_true')
    mode.add_argument('--refresh', type=Path, help='Refresh a campaign report from saved grades without model or worker calls')
    parser.add_argument('--resume', type=Path, help='Continue pending blocks in the given campaign without replaying partial blocks')
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--agent-only', action='store_true', help='Run new per-model calibration and agent blocks only')
    scope.add_argument('--recover-gemini', type=Path, help='Run only undispatched Gemini direct tasks and skipped receipts')
    scope.add_argument('--repeat-panel', action='store_true', help='Repeat 14 category-balanced direct tasks and eight receipts')
    args = parser.parse_args()
    if args.resume and not args.execute:
        parser.error('Use --resume only with --execute')
    if args.refresh and (args.agent_only or args.recover_gemini or args.repeat_panel):
        parser.error('Choose a benchmark scope only with --plan or --execute')
    try:
        if args.refresh:
            with meter_lock():
                refresh(args.refresh)
            print(f'Report: {args.refresh / "benchmark_report.md"}', flush=True)
            return 0
        packets = suites()
        recovery = None
        runs = local.ROOT / 'runs'
        if args.agent_only:
            packets = {name: packets[name] for name in ('calibration', 'agent')}
        if args.repeat_panel:
            packets = repeat_panel(packets)
        if args.recover_gemini:
            source = args.recover_gemini.resolve()
            if source.parent != runs.resolve() or not source.name.startswith('benchmark_day_'):
                raise ValueError('Gemini recovery requires a benchmark_day folder directly under runs')
            packets, recovery = gemini_recovery(source, packets)
        if args.plan:
            for name, suite in packets.items():
                print(f"{name}: {len(suite['tasks'])} distinct tasks per model")
            if args.repeat_panel:
                print('Repeat panel: ' + ', '.join(packets['direct']['task_ids']))
            if recovery:
                print('Gemini only; recorded and ambiguous attempts are excluded.')
            elif 'agent' in packets:
                print('Five models; one pass per section; the agent section requires successful per-model calibration.')
            else:
                print('Five models; one measured pass per section.')
            return 0
        worker = None
        if 'calibration' in packets or 'agent' in packets:
            worker = Worker()
            worker.check()
        env = dotenv_values(local.ROOT / '.env')
        keys = {name: (os.getenv(cfg['key_env']) or env.get(cfg['key_env']) or '').strip()
                for name, cfg in cloud.PROVIDERS.items() if recovery is None or name == 'gemini'}
        if any(not key or 'your-' in key for key in keys.values()):
            raise ValueError('Set OPENAI_API_KEY and GEMINI_API_KEY in .env before starting')
        config = yaml.safe_load((local.ROOT / 'config.yaml').read_text(encoding='utf-8'))
        folder = args.resume.resolve() if args.resume else runs / datetime.now(timezone.utc).strftime('benchmark_day_%Y%m%dT%H%M%S_%fZ')
        if folder.parent != runs.resolve() or not folder.name.startswith('benchmark_day_'):
            raise ValueError('Resume requires a benchmark_day folder directly under runs')
        with meter_lock():
            print(f'Benchmark records: {folder}', flush=True)
            status = execute(folder, packets, config, keys, worker, args.resume is not None, recovery)
        print(f'Benchmark status: {status}\nReport: {folder / "benchmark_report.md"}', flush=True)
        return 0 if status == 'complete' else 2
    except KeyboardInterrupt:
        print('Benchmark interrupted. Completed blocks and partial logs were saved.', flush=True)
        return 130
    except RECOVERABLE as exc:
        print(f'Benchmark stopped: {exc}', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
