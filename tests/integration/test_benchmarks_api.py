from studio.db import connect, create_benchmark_run
from studio.main import create_app
from fastapi.testclient import TestClient


def _setup(tmp_path, base):
    client = TestClient(create_app(tmp_path))
    saved = client.post(
        "/api/endpoints",
        json={"name": "local", "base_url": base, "kind": "openai"},
    )
    assert saved.status_code == 201, saved.text
    return client, saved.json()


def test_full_run_stores_timing(tmp_path, engine):
    state, base = engine
    state.usage = {"prompt_tokens": 5, "completion_tokens": 4}
    state.chunks = ["one", "two"]
    state.first_byte_delay = 0.15
    client, saved = _setup(tmp_path, base)
    response = client.post(
        "/api/benchmarks",
        json={"endpoint_id": saved["id"], "model": "demo-text", "warmup": False, "repeat_count": 1},
    )
    assert response.status_code == 200, response.text
    assert '"status": "done"' in response.text
    listing = client.get("/api/benchmarks").json()
    assert listing["runs"][0]["endpoint_name"] == "local"
    assert listing["runs"][0]["suite_version"] == "2"
    assert listing["runs"][0]["model"] == "demo-text"
    detail = client.get(f"/api/benchmarks/{listing['runs'][0]['id']}").json()
    assert [row["case_id"] for row in detail["results"]] == ["short", "longer", "reason", "code_python", "code_javascript"]
    first = detail["results"][0]
    assert first["ttft_ms"] >= 100
    assert first["output_tokens"] == 4
    assert first["tokens_per_second"] > 0
    exported = client.get(f"/api/benchmarks/{listing['runs'][0]['id']}/export")
    assert exported.headers["content-type"].startswith("application/json")
    assert "benchmark-" in exported.headers["content-disposition"]
    assert exported.json()["results"] == detail["results"]


def test_second_start_while_running_is_rejected(tmp_path, engine):
    _state, base = engine
    client, saved = _setup(tmp_path, base)
    with connect(client.app.state.db_path) as conn:
        create_benchmark_run(
            conn,
            endpoint_id=saved["id"],
            endpoint_kind="openai",
            model="demo-text",
            suite_version="1",
            warmup=True,
            repeat_count=1,
            status="running",
        )
    response = client.post(
        "/api/benchmarks",
        json={"endpoint_id": saved["id"], "model": "other", "warmup": False, "repeat_count": 1},
    )
    assert response.status_code == 409


def test_comparison_lists_same_suite_runs(tmp_path, engine):
    state, base = engine
    state.first_byte_delay = 0
    client, saved = _setup(tmp_path, base)
    for model in ("demo-text", "other-text"):
        response = client.post(
            "/api/benchmarks",
            json={"endpoint_id": saved["id"], "model": model, "warmup": False, "repeat_count": 1},
        )
        assert response.status_code == 200, response.text
    runs = client.get("/api/benchmarks").json()["runs"]
    assert {run["model"] for run in runs} == {"demo-text", "other-text"}
    assert {run["suite_version"] for run in runs} == {"2"}
    assert {run["endpoint_name"] for run in runs} == {"local"}


def test_code_profile_stores_full_output_and_progress(tmp_path, engine):
    import json
    state, base = engine
    state.chunks = ['def unique(items):\n    return list(dict.fromkeys(items))\n' * 12]
    client, saved = _setup(tmp_path, base)
    response = client.post('/api/benchmarks', json={
        'endpoint_id': saved['id'], 'model': 'demo-text', 'profile': 'code', 'warmup': False,
    })
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert events[0]['event'] == 'plan'
    assert events[0]['total'] == 2
    assert any(event.get('event') == 'case_started' for event in events)
    run_id = events[-1]['run_id']
    detail = client.get(f'/api/benchmarks/{run_id}').json()
    assert detail['run']['profile'] == 'code'
    assert {row['kind'] for row in detail['results']} == {'code'}
    assert detail['results'][0]['output_text'] == state.chunks[0]
    assert detail['summary']['completed'] == 2
    assert detail['summary']['total'] == 2


def test_failed_cases_are_not_reported_as_success(tmp_path, engine):
    state, base = engine
    state.chat_error = 'model unavailable'
    client, saved = _setup(tmp_path, base)
    response = client.post('/api/benchmarks', json={
        'endpoint_id': saved['id'], 'model': 'demo-text', 'warmup': False,
    })
    assert '"status": "error"' in response.text
    detail = client.get('/api/benchmarks/1').json()
    assert detail['summary']['completed'] == 0
    assert detail['summary']['median_tokens_per_second'] is None


def test_image_profile_saves_preview_and_uses_image_api(tmp_path, engine):
    import base64
    from studio.assets import IMAGE_PATH
    state, base = engine
    state.image_payload = {'data': [{'b64_json': base64.b64encode(IMAGE_PATH.read_bytes()).decode()}]}
    client, saved = _setup(tmp_path, base)
    response = client.post('/api/benchmarks', json={
        'endpoint_id': saved['id'], 'model': 'image-model', 'profile': 'image', 'warmup': False,
    })
    assert response.status_code == 200
    detail = client.get('/api/benchmarks/1').json()
    assert detail['run']['status'] == 'done'
    assert len(detail['results']) == 1
    result = detail['results'][0]
    assert result['kind'] == 'image'
    assert result['tokens_per_second'] is None
    assert result['ttft_ms'] is None
    assert result['total_ms'] >= 0
    image = client.get(result['image_url'])
    assert image.content == IMAGE_PATH.read_bytes()
    assert state.image_requests[0]['response_format'] == 'b64_json'
    assert not state.chat_requests


def test_unsupported_image_server_preserves_failed_report(tmp_path, engine):
    _state, base = engine
    client, saved = _setup(tmp_path, base)
    client.post('/api/benchmarks', json={
        'endpoint_id': saved['id'], 'model': 'demo-text', 'profile': 'image', 'warmup': False,
    })
    detail = client.get('/api/benchmarks/1').json()
    assert detail['run']['status'] == 'error'
    assert 'image generation' in detail['results'][0]['error'].lower()
    assert detail['results'][0]['image_url'] is None


def test_unknown_profile_rejected_without_creating_run(tmp_path, engine):
    _state, base = engine
    client, saved = _setup(tmp_path, base)
    response = client.post('/api/benchmarks', json={
        'endpoint_id': saved['id'], 'model': 'demo-text', 'profile': 'other',
    })
    assert response.status_code == 422
    assert client.get('/api/benchmarks').json()['runs'] == []


def test_warmup_failure_is_visible_and_does_not_leave_run_locked(tmp_path, engine):
    state, base = engine
    state.chat_error = 'not loaded'
    client, saved = _setup(tmp_path, base)
    client.post('/api/benchmarks', json={'endpoint_id': saved['id'], 'model': 'demo', 'warmup': True})
    detail = client.get('/api/benchmarks/1').json()
    assert detail['run']['status'] == 'error'
    assert 'Warmup failed' in detail['run']['error']
    assert detail['summary']['total'] == 5
    assert detail['summary']['completed'] == 0
    assert detail['summary']['comparison_key'] is None
    state.chat_error = None
    response = client.post('/api/benchmarks', json={'endpoint_id': saved['id'], 'model': 'demo', 'warmup': False})
    assert response.status_code == 200


def test_repeated_code_run_produces_comparable_summary(tmp_path, engine):
    state, base = engine
    state.first_byte_delay = .01
    client, saved = _setup(tmp_path, base)
    for _ in range(2):
        client.post('/api/benchmarks', json={'endpoint_id': saved['id'], 'model': 'demo', 'profile': 'code', 'repeat_count': 3, 'warmup': False})
    runs = client.get('/api/benchmarks').json()['runs']
    assert all(run['summary']['total'] == 6 for run in runs)
    assert runs[0]['summary']['comparison_key'] == runs[1]['summary']['comparison_key']
    assert runs[0]['summary']['comparison_key'] is not None


def test_missing_token_usage_is_labelled_as_chunk_estimate(tmp_path, engine):
    state, base = engine
    state.usage = None
    client, saved = _setup(tmp_path, base)
    client.post('/api/benchmarks', json={'endpoint_id': saved['id'], 'model': 'demo', 'profile': 'code', 'warmup': False})
    detail = client.get('/api/benchmarks/1').json()
    assert detail['summary']['token_basis'] == 'chunks'
    assert all(row['token_basis'] == 'chunks' for row in detail['results'])
