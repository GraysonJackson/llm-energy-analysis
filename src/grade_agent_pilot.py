"""Grade agent snapshots in isolated workers after all measured blocks finish."""

import json
import re


FUNCTION_CHECKS = r'''
import copy, importlib, inspect, json, sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
spec = json.load(sys.stdin)
fn = getattr(importlib.import_module(spec['module']), spec['function'])
if spec.get('group_by_must_be_keyword_only'):
    parameter = inspect.signature(fn).parameters['group_by']
    assert parameter.kind == parameter.KEYWORD_ONLY and parameter.default is None
if spec['function'] == 'subtotal':
    assert str(inspect.signature(fn)) == '(items)'
for case in spec['cases']:
    argument, kwargs = copy.deepcopy(case['input']), case.get('kwargs', {})
    if 'exception' in case:
        try:
            fn(argument, **kwargs)
        except ValueError:
            assert case['exception'] == 'ValueError'
        else:
            raise AssertionError('Expected ValueError')
    else:
        actual = fn(argument, **kwargs)
        expected = [tuple(x) for x in case['output_tuples']] if 'output_tuples' in case else case['output']
        assert actual == expected
    assert argument == case['input']
'''
TEST_ARGS = ['-m', 'unittest', 'discover', '-v']


def test_count(result):
    matches = re.findall(r'^Ran (\d+) tests? in ', result['output'], re.MULTILINE)
    return int(matches[-1]) if matches else 0


def grade_attempt(worker, task, criterion, attempt):
    task_id = task['item_id']
    files = attempt['files']
    originals = task['workspace_files']
    spec = criterion['verification']
    checks = {}
    feedback = {}

    def run(name, snapshot, args, stdin=''):
        result = worker.run(snapshot, args, stdin=stdin)
        feedback[name] = result
        return result

    checks['finished'] = attempt['status'] == 'finished'
    checks['public_verification_observed'] = attempt['public_verified']
    if task_id == 'P-A05':
        for index, case in enumerate(spec['cli_cases'], 1):
            snapshot = dict(files)
            if 'fixture' in case:
                snapshot[case['fixture']['path']] = case['fixture']['text']
            name = f'cli_case_{index}'
            result = run(name, snapshot, case['args'])
            checks[name] = (result['exit_code'] == case['expected_exit_code']
                            and result['output'] == case['expected_stdout'])
        function_case = spec['function_case']
        function_spec = {'module': function_case['module'], 'function': function_case['function'],
                         'cases': [{'input': function_case['input'], 'output': function_case['output']}]}
        result = run('public_function', files, ['-c', FUNCTION_CHECKS], json.dumps(function_spec))
        checks['public_function'] = result['exit_code'] == 0
        readme = files.get('README.md', '')
        checks['readme'] = ('python -m receipt_tool sample.csv' in readme
                            and re.search(r'(?<!\d)500(?!\d)', readme) is not None)
        checks['sample_unchanged'] = files.get('sample.csv') == originals['sample.csv']
    else:
        tests = run('submitted_tests', files, TEST_ARGS)
        checks['submitted_tests'] = tests['exit_code'] == 0 and test_count(tests) > 0
        if task_id == 'P-A03':
            filename = spec['unchanged_file']
            checks['unchanged_parser'] = files.get(filename) == originals[filename]
            mutants = [(filename, mutation['replace'], mutation['with']) for mutation in spec['mutations']]
        else:
            result = run('hidden_function_cases', files, ['-c', FUNCTION_CHECKS], json.dumps(spec))
            checks['hidden_function_cases'] = result['exit_code'] == 0
            filename = spec['module'] + '.py'
            # Run the original public cases independently of any submitted test changes.
            original_tests = {path: text for path, text in originals.items() if path.startswith('test_')}
            snapshot = {path: text for path, text in files.items() if not path.startswith('test_')}
            result = run('original_tests', {**snapshot, **original_tests}, TEST_ARGS)
            checks['original_tests'] = result['exit_code'] == 0 and test_count(result) > 0
            if task_id == 'P-A04':
                # This variant keeps the public base test passing while scrambling channel order.
                mutants = [(filename, 'in event["channels"]:', 'in sorted(event["channels"]):')]
            else:
                mutants = [(filename, originals[filename], originals[filename])]

        for index, (filename, before, after) in enumerate(mutants, 1):
            original = originals[filename]
            if before not in original:
                raise ValueError(f'Mutant definition does not match the original fixture for {task_id}')
            snapshot = {**files, filename: original.replace(before, after)}
            result = run(f'mutation_{index}', snapshot, TEST_ARGS)
            checks[f'mutation_{index}_caught'] = result['exit_code'] == 1 and test_count(result) > 0

    status = 'inadequate'
    if all(checks.values()):
        status = 'review_required' if task_id == 'P-A04' else 'adequate'
    return {'task_id': task_id, 'grade': status, 'checks': checks, 'worker_results': feedback}
