"""Prepare a blind direct-pilot review and refresh its comparison after offline grading."""

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from statistics import mean
from textwrap import indent

from run_direct_pilot import CONTEXT, DEADLINE, OUTPUT_LIMIT, persist
from score_receipt_pilot import score_attempt


def read_json(path):
    return json.loads(path.read_bytes())


def read_attempts(folder, manifest):
    tasks = manifest['task_ids']
    expected = {(task, repeat) for task in tasks for repeat in range(1, manifest['repetitions'] + 1)}
    by_model = {}
    for block in manifest['blocks']:
        with (folder / block['attempts_file']).open(encoding='utf-8') as source:
            rows = [json.loads(line) for line in source]
        pairs = {(row['task_id'], row['repetition']) for row in rows}
        model = block['model']
        if (len(rows) != len(expected) or pairs != expected or model in by_model
                or any(row['model'] != model for row in rows)):
            raise ValueError(f'Attempt log is incomplete or inconsistent for {model}')
        by_model[model] = rows
    return by_model


def load_direct_run(folder, version, task_hash, task_ids, models):
    manifest = read_json(folder / 'manifest.json')
    if (manifest['mode'] != 'local_direct_pilot' or manifest['dataset_version'] != version
            or manifest['task_packet_sha256'] != task_hash or manifest['task_ids'] != task_ids
            or manifest['models'] != models or manifest['repetitions'] < 1
            or manifest['context_tokens'] != CONTEXT or manifest['output_token_limit'] != OUTPUT_LIMIT
            or manifest['request_timeout_sec'] != DEADLINE):
        raise ValueError('Local run does not match the seven tasks, model list, or pilot limits')
    rows = read_attempts(folder, manifest)
    if set(rows) != set(models):
        raise ValueError('Local run is missing one or more models')
    return manifest, rows


def prepare_review(folder, cloud, tasks, scoring, local_run):
    local, local_rows = local_run
    cloud_rows = read_attempts(folder, cloud)
    sources = [('local', local, local_rows), ('cloud', cloud, cloud_rows)]
    key = {'dataset_version': cloud['dataset_version'], 'task_packet_sha256': cloud['task_packet_sha256'],
           'scoring_packet_sha256': cloud['scoring_packet_sha256'], 'scorer_version': scoring['scorer_version'],
           'tasks': {task['item_id']: task['domain'] for task in tasks}, 'runs': {}, 'answers': {}}
    rows_by_task = {task['item_id']: [] for task in tasks}
    for condition, manifest, by_model in sources:
        key['runs'][condition] = {
            'run_id': manifest['run_id'], 'status': manifest['status'], 'repetitions': manifest['repetitions'],
            'energy_scope': manifest['energy_scope'],
            'blocks': {block['model']: {'gross_joules': block['workload']['gross_joules'],
                                       'idle_adjusted_joules': block['incremental_batch_joules']}
                       for block in manifest['blocks']},
        }
        for rows in by_model.values():
            for row in rows:
                rows_by_task[row['task_id']].append((condition, row))

    rng = random.Random(cloud['run_id'])
    grades = {}
    review = ['# Blind review for the direct pilot', '',
              'Use only this packet while grading. In `review_grades.json`, replace each `null` with',
              '`"adequate"` or `"inadequate"`. An adequate reply satisfies the required criteria and',
              'avoids all automatic failures. Leave unanswered grades as `null`.', '',
              'For coding items, inspect a bare Python answer or a single Python code fence',
              'with no surrounding prose. Check the cases by inspection and grade this as a manual',
              'review. The pilot does not execute model-generated code.', '']
    for task in tasks:
        task_id = task['item_id']
        criteria = scoring['criteria'][task_id]
        verification = criteria.get('verification', {})
        shuffled = rows_by_task[task_id]
        rng.shuffle(shuffled)
        review.extend([f'## {task_id} {task["domain"].replace("_", " ")}', '', task['prompt'], '', 'Required', ''])
        review.extend(f'- {line}' for line in criteria['required'])
        review.extend(['', 'Automatic failures', ''])
        review.extend(f'- {line}' for line in criteria['automatic_failure'])
        if verification.get('cases'):
            review.extend(['', 'Reference cases', '', indent(json.dumps(verification, indent=2), '    ')])
        for index, (condition, row) in enumerate(shuffled, 1):
            answer_id = f'{task_id}-{index:02}'
            info = {field: row[field] for field in ('task_id', 'model', 'repetition', 'status', 'duration_sec')}
            info['condition'] = condition
            if row['status'] != 'completed':
                info.update(grade='inadequate', reason=row['status'])
            elif 'expected_json' in verification:
                result = score_attempt(row, verification['expected_json'])
                info.update(grade='adequate' if result['pass'] else 'inadequate', reason=result['reason'])
            else:
                info.update(grade=None, reason='manual_review')
                grades[answer_id] = None
                review.extend(['', f'### {answer_id}', '', indent(row['raw_response']['response'], '    ')])
            key['answers'][answer_id] = info
        review.append('')

    (folder / 'review_packet.md').write_text('\n'.join(review), encoding='utf-8')
    persist(folder / 'review_key.json', key)
    persist(folder / 'review_grades.json', grades)
    write_comparison(folder)
    return len(grades)


def write_comparison(folder):
    key = read_json(folder / 'review_key.json')
    grades = read_json(folder / 'review_grades.json')
    answers = key['answers']
    expected = {answer_id for answer_id, row in answers.items() if row['grade'] is None}
    if not isinstance(grades, dict) or grades.keys() != expected:
        raise ValueError('Keep the original answer IDs in review_grades.json')
    if any(grade not in (None, 'adequate', 'inadequate') for grade in grades.values()):
        raise ValueError('Grades must be "adequate", "inadequate", or null')
    results = {name: key[name] for name in ('dataset_version', 'task_packet_sha256', 'scoring_packet_sha256',
                                            'scorer_version', 'tasks', 'runs')}
    results['pending_manual_grades'] = sum(grade is None for grade in grades.values())
    results['energy_basis'] = ('Full measured block, including failed attempts. See each run for its repetition '
                               'count and energy scope. Cloud power covers the client workstation only.')
    results['models'] = []
    for condition, run in key['runs'].items():
        for model, energy in run['blocks'].items():
            rows = [{**row, 'grade': grades.get(answer_id, row['grade'])}
                    for answer_id, row in answers.items() if row['model'] == model and row['condition'] == condition]
            by_task = {}
            for task_id, domain in key['tasks'].items():
                matching = [row for row in rows if row['task_id'] == task_id]
                counts = Counter(row['grade'] for row in matching)
                first, = [row for row in matching if row['repetition'] == 1]
                by_task[task_id] = {'category': domain, 'attempts': len(matching), 'adequate': counts['adequate'],
                                    'inadequate': counts['inadequate'], 'pending': counts[None],
                                    'mean_sec': mean(row['duration_sec'] for row in matching),
                                    'first_attempt_grade': first['grade'], 'first_attempt_sec': first['duration_sec']}
            adequate = sum(task['adequate'] for task in by_task.values())
            final = all(task['pending'] == 0 for task in by_task.values())
            results['models'].append({
                'model': model, 'condition': condition, 'attempts': len(rows),
                'attempt_statuses': dict(Counter(row['status'] for row in rows)),
                'mean_sec': mean(row['duration_sec'] for row in rows), 'by_task': by_task,
                'batch_energy': energy,
                'joules_per_adequate_response': {metric: value / adequate if final and adequate and value is not None
                                                  else None for metric, value in energy.items()},
            })
    persist(folder / 'direct_comparison.json', results)
    return results['pending_manual_grades']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_folder', type=Path, help='Cloud direct pilot results folder')
    args = parser.parse_args()
    try:
        pending = write_comparison(args.run_folder)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(f'Comparison: {args.run_folder / "direct_comparison.json"} ({pending} pending manual grades)')


if __name__ == '__main__':
    main()
