"""Score generated receipt responses as data, without executing model output."""

import json
from collections import Counter


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError(f'Invalid JSON constant: {value}')


def same_value(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(same_value(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same_value(left, right) for left, right in zip(actual, expected))
    return actual == expected


def score_attempt(row, expected):
    if row['status'] != 'completed':
        return {'pass': False, 'reason': row['status']}
    response = row['raw_response']['response']
    try:
        actual = json.loads(response, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    except ValueError as exc:
        return {'pass': False, 'reason': 'invalid_raw_json', 'detail': str(exc)}

    if not isinstance(actual, dict) or actual.keys() != expected.keys():
        return {'pass': False, 'reason': 'wrong_object_keys'}
    wrong = [key for key, value in expected.items() if not same_value(actual[key], value)]
    if wrong:
        return {'pass': False, 'reason': 'wrong_value_or_type', 'fields': wrong}
    return {'pass': True, 'reason': 'exact_match'}


def score_run(folder, manifest, scoring):
    """Combine strict passes with measured batch energy, including failed responses."""
    expected_by_task = scoring['expected_by_task']
    task_ids = manifest['task_ids']
    expected_attempts = {(task_id, repeat) for task_id in task_ids
                         for repeat in range(1, manifest['repetitions'] + 1)}
    results = []
    for block in manifest['blocks']:
        with (folder / block['attempts_file']).open(encoding='utf-8') as source:
            rows = [json.loads(line) for line in source]
        seen = {(row['task_id'], row['repetition']) for row in rows}
        if (len(rows) != len(expected_attempts) or seen != expected_attempts
                or any(row['model'] != block['model'] for row in rows)):
            raise ValueError(f"Receipt attempt log is incomplete or inconsistent for {block['model']}")

        attempts = []
        by_task = Counter()
        for row in rows:
            task_id = row['task_id']
            result = score_attempt(row, expected_by_task[task_id])
            by_task[task_id] += int(result['pass'])
            attempts.append({'task_id': task_id, 'repetition': row['repetition'],
                             'duration_sec': row['duration_sec'], **result})

        passes = sum(by_task.values())
        gross = block['workload']['gross_joules']
        adjusted = block['incremental_batch_joules']
        results.append({
            'model': block['model'],
            'passes': passes,
            'attempts': len(rows),
            'passes_by_task': {task_id: by_task[task_id] for task_id in task_ids},
            'mean_response_sec': sum(row['duration_sec'] for row in rows) / len(rows),
            'gross_batch_joules': gross,
            'idle_adjusted_batch_joules': adjusted,
            'gross_joules_per_valid_response': gross / passes if gross is not None and passes else None,
            'idle_adjusted_joules_per_valid_response': adjusted / passes if adjusted is not None and passes else None,
            'attempt_scores': attempts,
        })
    return {
        'run_id': manifest['run_id'],
        'dataset_version': manifest['dataset_version'],
        'task_packet_sha256': manifest['task_packet_sha256'],
        'scoring_packet_sha256': manifest['scoring_packet_sha256'],
        'scorer_version': scoring['scorer_version'],
        'task_ids': task_ids,
        'energy_basis': 'Measured batch energy divided by the number of strict passes, including failed attempts.',
        'model_results': results,
    }
