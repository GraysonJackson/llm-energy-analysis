"""Validate and combine the saved November benchmark, its recovery and the v3 agent run."""

import argparse
import csv
import json
import math
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path
from statistics import median

from pilot_power import integrate
from run_benchmark_day import refresh, suites
from run_direct_pilot import persist
from score_receipt_pilot import score_attempt


REVIEWERS = ('luna_a', 'luna_b', 'luna_c')
REFACTOR_FIELDS = ('shared_channel_loop', 'explains_order')


def read(path):
    return json.loads(path.read_bytes())


def blind_votes(folder):
    mapping = read(folder / 'answer_map_private.json')
    ballots = {}
    for reviewer in REVIEWERS:
        votes = {}
        for packet in sorted((folder / 'blind').glob('*.json')):
            entries = read(packet)
            refactor = packet.stem == 'agent_refactor'
            expected = {entry['id'] for entry in entries} if refactor else {
                answer['id'] for task in entries for answer in task['answers']}
            submitted = read(folder / reviewer / packet.name)
            if submitted.keys() != expected or expected & votes.keys():
                raise ValueError(f'Invalid ballot IDs in {reviewer}/{packet.name}')
            for answer_id, ballot in submitted.items():
                fields = REFACTOR_FIELDS if refactor else ('vote',)
                if ballot.keys() != {'reason', *fields} or not isinstance(ballot['reason'], str) or not ballot['reason'].strip():
                    raise ValueError(f'Missing vote or explanation for {reviewer}/{answer_id}')
                if refactor and any(type(ballot[field]) is not bool for field in fields):
                    raise ValueError(f'Invalid refactor vote for {reviewer}/{answer_id}')
                if not refactor and ballot['vote'] not in ('adequate', 'inadequate'):
                    raise ValueError(f'Invalid direct vote for {reviewer}/{answer_id}')
            votes.update(submitted)
        if votes.keys() != mapping.keys():
            raise ValueError(f'Incomplete ballot for {reviewer}')
        ballots[reviewer] = votes

    results = {}
    for answer_id, item in mapping.items():
        votes = {reviewer: ballot[answer_id] for reviewer, ballot in ballots.items()}
        fields = REFACTOR_FIELDS if item['type'] == 'refactor' else ('vote',)
        counts = {field: Counter(ballot[field] for ballot in votes.values()) for field in fields}
        results[answer_id] = {
            **item, 'votes': votes,
            'majority': {field: tally.most_common(1)[0][0] for field, tally in counts.items()},
            'unanimous': all(len(tally) == 1 for tally in counts.values()),
        }
    return results


def apply_votes(consensus, original, recovery, agent):
    votes = blind_votes(consensus)
    direct = defaultdict(dict)
    refactors = {}
    for item in votes.values():
        if item['type'] == 'refactor':
            refactors[item['answer']] = item['majority']
        else:
            direct[item['side']][item['answer']] = item['majority']['vote']

    updates = {original / 'direct' / 'review_grades.json': direct['original'],
               recovery / 'direct' / 'review_grades.json': direct['recovery'],
               agent / 'agent' / 'refactor_review.json': refactors}
    old = {}
    for path, grades in updates.items():
        old[path] = read(path)
        if old[path].keys() != grades.keys():
            raise ValueError(f'Ballot answers do not match {path}')
        if path.name == 'review_grades.json' and any(v is not None and v != grades[key] for key, v in old[path].items()):
            raise ValueError(f'Existing direct grades disagree with consensus in {path}')
    previous = consensus / 'grades_before_consensus.json'
    if not previous.exists():
        persist(previous, {f'{path.parent.parent.name}/{path.parent.name}/{path.name}': value
                           for path, value in old.items()})
    persist(consensus / 'consensus_votes.json', votes)
    persist(consensus / 'gemini_partial_grades.json', direct['gemini_partial'])
    for path, grades in updates.items():
        persist(path, grades)
    for folder in (original, recovery, agent):
        refresh(folder)
    return votes


def attempt_rows(folder, block):
    if 'attempts' in block:
        return [read(folder / path) for path in block['attempts'].values()]
    return [json.loads(line) for line in (folder / block['attempts_file']).read_text(encoding='utf-8').splitlines()]


def trace_samples(folder, window):
    with (folder / window['trace_file']).open(newline='', encoding='utf-8') as source:
        samples = [((float(row['request_start_elapsed_sec']) + float(row['request_end_elapsed_sec'])) / 2,
                    float(row['power_w']) if row['power_w'] else None) for row in csv.DictReader(source)]
    if len(samples) != window['attempted_samples'] or any(a[0] >= b[0] for a, b in zip(samples, samples[1:])):
        raise ValueError(f'Invalid sample count or order in {folder / window["trace_file"]}')
    value, reason = integrate(samples, window['started_elapsed_sec'], window['ended_elapsed_sec'],
                              window['max_allowed_gap_sec'])
    recorded = window['gross_joules']
    if (value is None) != (recorded is None) or (value is not None and not math.isclose(value, recorded, abs_tol=1e-6)):
        raise ValueError(f'Trace integral differs from the manifest in {folder / window["trace_file"]}')
    return samples, reason


def direct_grades(folder):
    key = read(folder / 'review_key.json')['answers']
    votes = read(folder / 'review_grades.json')
    return {(item['model'], item['task_id']): votes.get(answer_id, item['grade'])
            for answer_id, item in key.items()}


def collect(original, recovery, agent_folder, partial_grades):
    packets = suites()
    direct_suite, receipt_suite = packets['direct'], packets['receipts']
    category = {task['item_id']: task['domain'] for task in direct_suite['tasks']}
    grade_by_run = {folder: direct_grades(folder / 'direct') for folder in (original, recovery)}
    agent_grades = {(model['model'], attempt['task_id']): attempt['grade']
                    for model in read(agent_folder / 'agent' / 'agent_scores.json')['models']
                    for attempt in model['attempts']}
    rows = {}
    blocks = []
    trace_count = 0
    manifests = {folder: read(folder / 'manifest.json') for folder in (original, recovery, agent_folder)}
    if manifests[recovery]['recovery']['source_run'] != original.name:
        raise ValueError('Recovery does not reference the selected original campaign')
    if manifests[agent_folder]['agent_protocol'] != 'structured-one-action-v3':
        raise ValueError('Expected the v3 agent run')
    for folder in (original, recovery, agent_folder):
        manifest = manifests[folder]
        sections = ('agent',) if folder == agent_folder else ('direct', 'receipts')
        for section in sections:
            fingerprints = manifest['fingerprints'][section]
            spec = packets[section]
            if (fingerprints[1] != spec['scoring_packet_sha256'] or
                    (folder != recovery or section != 'direct') and fingerprints[0] != spec['task_packet_sha256']):
                raise ValueError(f'Tasks or rubric changed for {section} in {folder.name}')
            for entry in manifest['sections'][section]:
                block = entry.get('block', {})
                if 'workload' not in block:
                    continue
                model = entry['model']
                source = folder / section
                work = block['workload']
                idle = block.get('idle') or block.get('workstation_idle') or block['loaded_idle']
                samples, _ = trace_samples(source, work)
                trace_samples(source, idle)
                trace_count += 2
                block_delta = block.get('idle_adjusted_joules', block.get('incremental_batch_joules'))
                if block_delta is not None and not math.isclose(
                        block_delta, work['gross_joules'] - idle['mean_watts'] * work['duration_sec'], abs_tol=1e-6):
                    raise ValueError(f'Idle adjustment differs from the manifest in {source}')
                attempts = attempt_rows(source, block)
                placement = block.get('placement_before_work') or entry.get('placement') or {}
                if entry['condition'] == 'local':
                    if not placement.get('digest'):
                        raise ValueError(f'Missing local model digest for {model}')
                    revisions = [placement['digest']]
                else:
                    reported = [turn for row in attempts for turn in row['turns']] if section == 'agent' else attempts
                    revisions = sorted({row['returned_model'] for row in reported if row.get('returned_model')})
                block_result = {'run': folder.name, 'section': section, 'model': model, 'condition': entry['condition'],
                                'status': entry['status'], 'gross_joules': work['gross_joules'],
                                'idle_adjusted_joules': block_delta, 'adequate': 0, 'attempts': len(attempts),
                                'reported_revisions': revisions}
                blocks.append(block_result)
                for attempt in attempts:
                    task, status = attempt['task_id'], attempt['status']
                    key = section, model, task
                    if key in rows or attempt['model'] != model:
                        raise ValueError(f'Duplicate or mismatched attempt {key}')
                    if section == 'agent':
                        grade = agent_grades[model, task]
                    elif section == 'receipts':
                        expected = receipt_suite['scoring']['expected_by_task'][task]
                        grade = 'adequate' if score_attempt(attempt, expected)['pass'] else 'inadequate'
                    elif (model, task) in grade_by_run[folder]:
                        grade = grade_by_run[folder][model, task]
                    elif status != 'completed':
                        grade = 'inadequate'
                    else:
                        spec = direct_suite['scoring']['criteria'][task].get('verification', {})
                        if 'expected_json' in spec:
                            grade = 'adequate' if score_attempt(attempt, spec['expected_json'])['pass'] else 'inadequate'
                        else:
                            grade = partial_grades[task]
                    if grade not in ('adequate', 'inadequate'):
                        raise ValueError(f'Unresolved grade for {key}')
                    start, end = attempt['started_elapsed_sec'], attempt['ended_elapsed_sec']
                    if not work['started_elapsed_sec'] <= start <= end <= work['ended_elapsed_sec']:
                        raise ValueError(f'Attempt window falls outside its saved trace for {key}')
                    energy, reason = integrate(samples, start, end, work['max_allowed_gap_sec'])
                    incremental = energy - idle['mean_watts'] * (end - start) if energy is not None and block_delta is not None else None
                    rows[key] = {'section': section, 'model': model, 'condition': entry['condition'], 'task_id': task,
                                 'category': category[task] if section == 'direct' else section, 'status': status,
                                 'grade': grade, 'latency_sec': attempt['duration_sec'], 'gross_joules': energy,
                                 'idle_adjusted_joules': incremental, 'coverage_issue': reason, 'run': folder.name}
                    block_result['adequate'] += grade == 'adequate'
    model_names = {condition[1] for condition in manifests[original]['conditions']}
    expected = {(name, model, task) for name in ('direct', 'receipts', 'agent')
                for model in model_names for task in packets[name]['task_ids']}
    if rows.keys() != expected:
        missing = expected - rows.keys()
        extra = rows.keys() - expected
        raise ValueError(f'Campaign coverage mismatch, {len(missing)} missing and {len(extra)} extra attempts')
    for model in model_names:
        revisions = {revision for block in blocks if block['model'] == model for revision in block['reported_revisions']}
        if len(revisions) != 1:
            raise ValueError(f'Inconsistent model revisions reported for {model}')
    return rows, blocks, trace_count


def matched_energy(rows):
    pairs = []
    for section in ('direct', 'receipts', 'agent'):
        groups = defaultdict(dict)
        for record in rows.values():
            if record['section'] == section:
                groups[record['condition'], record['model']][record['task_id']] = record
        for (condition, local), first in groups.items():
            if condition != 'local':
                continue
            for (kind, cloud), second in groups.items():
                if kind != 'cloud':
                    continue
                common = [task for task in first.keys() & second.keys()
                          if first[task]['grade'] == second[task]['grade'] == 'adequate']
                metrics = {}
                for metric in ('gross_joules', 'idle_adjusted_joules'):
                    values = {task: (first[task][metric] - second[task][metric]) / 3600 for task in sorted(common)
                              if first[task][metric] is not None and second[task][metric] is not None}
                    metrics[metric] = {'n': len(values), 'median_wh': median(values.values()) if values else None,
                                       'task_threshold_wh': values}
                pairs.append({'section': section, 'local': local, 'cloud': cloud, 'common_adequate': len(common), **metrics})
    return pairs


def ledger_snapshot(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        rows = db.execute('''SELECT provider, COUNT(*), COALESCE(SUM(settled), 0),
                          COALESCE(SUM(CASE WHEN settled IS NULL THEN reserved ELSE 0 END), 0)
                          FROM cloud_requests GROUP BY provider ORDER BY provider''').fetchall()
    return [{'provider': provider, 'requests': count, 'settled_microdollars': spent, 'held_microdollars': held}
            for provider, count, spent, held in rows]


def write_analysis(output, rows, blocks, trace_count, votes, budget=None):
    output.mkdir(parents=True, exist_ok=True)
    records = sorted(rows.values(), key=lambda row: (row['section'], row['model'], row['task_id']))
    with (output / 'attempt_energy.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    pairs = matched_energy(rows)
    grouped = defaultdict(list)
    for row in records:
        grouped[row['section'], row['model'], row['category']].append(row)
    summaries = [{'section': section, 'model': model, 'category': category, 'attempts': len(items),
                  'adequate': sum(row['grade'] == 'adequate' for row in items),
                  'gross_energy_covered': sum(row['gross_joules'] is not None for row in items),
                  'adjusted_energy_covered': sum(row['idle_adjusted_joules'] is not None for row in items),
                  'median_latency_sec': median(row['latency_sec'] for row in items)}
                 for (section, model, category), items in grouped.items()]
    audit = {kind: dict(Counter('unanimous' if entry['unanimous'] else 'split' for entry in votes.values()
                                if entry['type'] == kind)) for kind in ('direct', 'refactor')}
    persist(output / 'analysis.json', {'agreement': audit, 'verified_traces': trace_count, 'break_even': pairs,
                                       'categories': summaries, 'blocks': blocks, 'budget': budget})
    lines = ['# Adjudicated benchmark analysis', '',
             f'{len(records)} attempts and {trace_count} raw trace integrals verified.', '',
             'Three independent Luna sessions reviewed each submitted blind item. The majority decided each verdict.',
             'The reviewers received packets without model or session labels. They used the same model family,',
             'so agreement is evidence about this panel and should not be treated as independent human validation.', '']
    for kind, counts in audit.items():
        lines.append(f"- {kind.capitalize()} reviews: {counts.get('unanimous', 0)} unanimous and {counts.get('split', 0)} split.")
    lines.extend(['', '## Results at a glance', '',
                  '| Model | Direct adequate / attempted | Strict receipts passed / attempted | Agent tasks passed / attempted |',
                  '| --- | ---: | ---: | ---: |'])
    for model in sorted({row['model'] for row in records}):
        cells = []
        for section in ('direct', 'receipts', 'agent'):
            selected = [row for row in records if row['model'] == model and row['section'] == section]
            cells.append(f"{sum(row['grade'] == 'adequate' for row in selected)}/{len(selected)}")
        lines.append(f'| {model} | ' + ' | '.join(cells) + ' |')
    lines.extend(['', '## Quality and latency by category', '',
                  '| Section | Model | Category | Adequate / attempted | Median latency (s) | Task energy covered, gross / adjusted |',
                  '| --- | --- | --- | ---: | ---: | ---: |'])
    for row in summaries:
        label = row['category'].replace('_', ' ')
        lines.append(f"| {row['section']} | {row['model']} | {label} | {row['adequate']}/{row['attempts']} | "
                     f"{row['median_latency_sec']:.2f} | {row['gross_energy_covered']} / {row['adjusted_energy_covered']} |")
    lines.extend(['', '## Batch electricity', '',
                  'Batch energy includes failed attempts and between-request overhead inside the measurement window.',
                  'Gemini’s two direct batches have separate idle conditions. Keep their traces separate.', '',
                  '| Section | Model | Time (UTC run ID) | Passes / attempts | Gross (Wh) | Idle adjusted (Wh) | Gross (Wh/pass) |',
                  '| --- | --- | --- | ---: | ---: | ---: | ---: |'])
    def wh(joules):
        return '—' if joules is None else f'{joules / 3600:.3f}'

    for block in blocks:
        gross, adequate = block['gross_joules'], block['adequate']
        lines.append(f"| {block['section']} | {block['model']} | {block['run'].removeprefix('benchmark_day_')} | "
                     f"{adequate}/{block['attempts']} | {wh(gross)} | {wh(block['idle_adjusted_joules'])} | "
                     f"{wh(gross / adequate if gross is not None and adequate else None)} |")
    lines.extend(['', '## Matched cloud-server break-even thresholds', '',
                  'Each pair uses only tasks both models passed and with enough samples in both attempt windows.',
                  'Subtract cloud-client electricity from local electricity. The difference is the server allowance',
                  'that would bring the two totals to parity, with network electricity excluded. A negative value',
                  'means the measured cloud client already used more electricity for that task.',
                  'These are descriptive thresholds. Server electricity itself was unavailable.', '',
                  '| Section | Local | Cloud | Common passes | Gross median (Wh), n | Adjusted median (Wh), n |',
                  '| --- | --- | --- | ---: | ---: | ---: |'])
    def threshold(metric):
        return '—' if metric['median_wh'] is None else f"{metric['median_wh']:.3f}, {metric['n']}"

    for pair in pairs:
        lines.append(f"| {pair['section']} | {pair['local']} | {pair['cloud']} | {pair['common_adequate']} | "
                     f"{threshold(pair['gross_joules'])} | {threshold(pair['idle_adjusted_joules'])} |")
    if budget:
        lines.extend(['', '## API ledger', '',
                      'Cumulative conservative estimates through the saved follow-ups, before credits or discounts.', '',
                      '| Provider | Requests reserved | Settled estimate | Unsettled reservation |',
                      '| --- | ---: | ---: | ---: |'])
        for row in budget:
            lines.append(f"| {row['provider']} | {row['requests']} | ${row['settled_microdollars'] / 1e6:.4f} | "
                         f"${row['held_microdollars'] / 1e6:.4f} |")
    lines.extend(['', '## Evidence and limits', '',
                  '- Short attempts can have too few interior samples for individual energy integration. Batch totals remain separate.',
                  '- Retain negative idle-adjusted values. Baseline drift or missing coverage can make an adjusted estimate unavailable.',
                  '- Cloud API account controls, actual invoices and offline local inference are separate verification items.',
                  '- The run contains one measured attempt per model and task. It does not estimate repeatability across sessions.',
                  '- Published Gemini Apps measurements describe a different product and workload. Large-scale inference models offer useful context, but the break-even calculation leaves API server draw unmeasured.',
                  '  [Google production measurement](https://services.google.com/fh/files/misc/measuring_the_environmental_impact_of_delivering_ai_at_google_scale.pdf) · [Oviedo et al., Joule](https://doi.org/10.1016/j.joule.2026.102430)',
                  '', '[Per-attempt evidence](attempt_energy.csv) · [Full numeric analysis](analysis.json)', ''])
    (output / 'analysis.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('recovery', type=Path)
    parser.add_argument('agent', type=Path)
    args = parser.parse_args()
    consensus = args.original / 'consensus'
    try:
        votes = apply_votes(consensus, args.original, args.recovery, args.agent)
        partial = read(consensus / 'gemini_partial_grades.json')
        rows, blocks, trace_count = collect(args.original, args.recovery, args.agent, partial)
        ledger = ledger_snapshot(args.original.parent / 'cloud_budget.sqlite3')
        write_analysis(args.original / 'analysis', rows, blocks, trace_count, votes, ledger)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        parser.error(str(exc))
    print(f'Verified {len(votes)} majority reviews, {len(rows)} attempts, and {trace_count} trace integrals.')
    print(args.original / 'analysis' / 'analysis.md')


if __name__ == '__main__':
    main()
