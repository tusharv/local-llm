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
    assert listing["runs"][0]["suite_version"] == "1"
    assert listing["runs"][0]["model"] == "demo-text"
    detail = client.get(f"/api/benchmarks/{listing['runs'][0]['id']}").json()
    assert [row["case_id"] for row in detail["results"]] == ["short", "longer", "reason"]
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
    assert {run["suite_version"] for run in runs} == {"1"}
    assert {run["endpoint_name"] for run in runs} == {"local"}
