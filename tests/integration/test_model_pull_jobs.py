import threading
import time

from fastapi.testclient import TestClient
from studio.main import create_app


def test_pull_survives_browser_and_deduplicates(tmp_path, monkeypatch):
    release = threading.Event()
    started = threading.Event()
    calls = []

    def pull(*args):
        calls.append(args)
        started.set()
        yield {"status": "downloading", "completed": 25, "total": 100}
        assert release.wait(5)
        yield {"status": "success"}

    monkeypatch.setattr("studio.pulls.iter_pull", pull)
    app = create_app(tmp_path)
    first = TestClient(app)
    endpoint = first.post("/api/endpoints", json={"name":"Local", "kind":"ollama", "base_url":"http://127.0.0.1:11434/v1"}).json()
    body = {"endpoint_id": endpoint["id"], "name":"test:1b"}
    try:
        result = first.post("/api/model-pulls", json=body)
        assert result.status_code == 202
        assert started.wait(2)
        first.close()
        browser = TestClient(app)
        status = browser.get("/api/model-pulls", params={"endpoint_id":endpoint["id"]}).json()["job"]
        assert status["state"] == "running"
        duplicate = browser.post("/api/model-pulls", json=body).json()["job"]
        assert duplicate["id"] == status["id"]
        assert browser.post("/api/model-pulls", json={**body, "name":"other"}).status_code == 409
        assert len(calls) == 1
    finally:
        release.set()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        job = app.state.pulls.get(endpoint["id"])
        if job["state"] != "running":
            break
        time.sleep(.01)
    assert job["state"] == "done"
    assert create_app(tmp_path).state.pulls.get(endpoint["id"])["state"] == "done"


def test_pull_records_stream_failure_and_restart(tmp_path, monkeypatch):
    def broken(*args):
        yield {"error":"model not found"}
    monkeypatch.setattr("studio.pulls.iter_pull", broken)
    app = create_app(tmp_path)
    manager = app.state.pulls
    job = manager.start({"id":1, "base_url":"http://127.0.0.1:11434/v1"}, "missing")
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and manager.get(1)["state"] == "running":
        time.sleep(.01)
    assert manager.get(1)["error"] == "model not found"
    job.update(state="running")
    manager._save(job)
    restored = create_app(tmp_path).state.pulls.get(1)
    assert restored["state"] == "error"
    assert "restarted" in restored["error"]
