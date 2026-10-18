from urllib.parse import quote

from fastapi.testclient import TestClient

from studio.main import create_app


def _client(tmp_path):
    return TestClient(create_app(tmp_path))


def _save(client, base_url, kind):
    response = client.post(
        "/api/endpoints",
        json={"name": kind, "base_url": base_url, "kind": kind},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_pull_and_delete_are_rejected_for_openai(tmp_path, engine):
    state, base = engine
    client = _client(tmp_path)
    saved = _save(client, base, "openai")
    pull = client.post("/api/models/pull", json={"endpoint_id": saved["id"], "name": "llama3:8b"})
    delete = client.delete(f"/api/models/{quote('llama3:8b', safe='')}?endpoint_id={saved['id']}")
    assert pull.status_code == 400
    assert delete.status_code == 400
    assert state.pulls == []
    assert state.deleted == []


def test_ollama_lists_vision_and_streams_pull(tmp_path, engine):
    state, base = engine
    state.models = ["llava:7b"]
    state.show_by_name["llava:7b"] = {
        "capabilities": ["vision"],
        "details": {"family": "llava"},
        "size": 4096,
    }
    client = _client(tmp_path)
    saved = _save(client, base, "ollama")
    listed = client.get("/api/models", params={"endpoint_id": saved["id"]})
    assert listed.status_code == 200
    model = listed.json()["models"][0]
    assert model["id"] == "llava:7b"
    assert model["vision"] is True
    assert model["vision_source"] == "capabilities"
    assert model["family"] == "llava"
    assert model["size_bytes"] == 4096
    pull = client.post("/api/models/pull", json={"endpoint_id": saved["id"], "name": "llama3:8b"})
    assert pull.status_code == 200
    assert "pulling" in pull.text
    assert '"done": true' in pull.text
    assert state.pulls == ["llama3:8b"]
    deleted = client.delete(f"/api/models/{quote('llama3:8b', safe='')}?endpoint_id={saved['id']}")
    assert deleted.status_code == 200
    assert state.deleted == ["llama3:8b"]


def test_vision_override_is_returned(tmp_path, engine):
    state, base = engine
    state.models = ["demo-text"]
    client = TestClient(create_app(tmp_path))
    saved = _save(client, base, "openai")
    updated = client.put(
        "/api/models/flags",
        json={"endpoint_id": saved["id"], "model": "demo-text", "vision_override": "on"},
    )
    assert updated.status_code == 200
    assert updated.json()["vision"] is True
    listed = client.get("/api/models", params={"endpoint_id": saved["id"]})
    assert listed.json()["models"][0]["vision_source"] == "override"
