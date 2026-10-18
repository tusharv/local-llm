from studio.benchmarks.report import summarize


def test_medians_exclude_failures_and_missing_values():
    run = {'suite_version': '2', 'profile': 'code', 'repeat_count': 3, 'warmup': True, 'expected_results': 3}
    rows = [
        {'case_id': 'code_python', 'kind': 'code', 'ttft_ms': 100, 'total_ms': 1000, 'tokens_per_second': 10, 'error': None, 'token_basis': 'tokens'},
        {'case_id': 'code_python', 'kind': 'code', 'ttft_ms': 300, 'total_ms': 3000, 'tokens_per_second': 30, 'error': None, 'token_basis': 'tokens'},
        {'case_id': 'code_python', 'kind': 'code', 'ttft_ms': 9000, 'total_ms': 9000, 'tokens_per_second': 1000, 'error': 'failed'},
    ]
    summary = summarize(run, rows)
    assert summary['completed'] == 2
    assert summary['total'] == 3
    assert summary['median_ttft_ms'] == 200
    assert summary['median_tokens_per_second'] == 20
    assert summary['cases'][0]['median_total_ms'] == 2000
    assert summary['comparison_key'] is None  # Failed runs are not comparable.


def test_comparison_key_separates_profiles_warmup_and_token_basis():
    run = {'suite_version': '2', 'profile': 'code', 'repeat_count': 1, 'warmup': True, 'expected_results': 1}
    rows = [{'case_id': 'code_python', 'kind': 'code', 'token_basis': 'tokens', 'error': None}]
    first = summarize(run, rows)['comparison_key']
    assert first
    assert first != summarize({**run, 'warmup': False}, rows)['comparison_key']
    assert first != summarize(run, [{**rows[0], 'token_basis': 'chunks'}])['comparison_key']
    assert first != summarize({**run, 'suite_version': '1'}, rows)['comparison_key']


def test_empty_report_has_no_fabricated_speed():
    summary = summarize({'expected_results': 2}, [])
    assert summary['completed'] == 0
    assert summary['total'] == 2
    assert summary['median_ttft_ms'] is None
    assert summary['median_tokens_per_second'] is None
