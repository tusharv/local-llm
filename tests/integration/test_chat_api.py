from fastapi.testclient import TestClient

from studio.main import create_app


def _client(tmp_path):
    return TestClient(create_app(tmp_path))


def _endpoint(client, base_url, kind="openai", name="local", confirmed=False):
    response = client.post(
        "/api/endpoints",
        json={
            "name": name,
            "base_url": base_url,
            "kind": kind,
            "private_network_confirmed": confirmed,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_stream_reload_and_delete(tmp_path, engine):
    state, base = engine
    state.chunks = ["Hello"]
    client = _client(tmp_path)
    saved = _endpoint(client, base)
    created = client.post("/api/conversations", json={"endpoint_id": saved["id"], "model": "demo-text"})
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    streamed = client.post("/api/chat", json={"conversation_id": conversation_id, "content": "Hi"})
    assert streamed.status_code == 200
    assert "Hello" in streamed.text
    loaded = client.get(f"/api/conversations/{conversation_id}")
    messages = loaded.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "Hello"
    again = TestClient(create_app(tmp_path))
    reloaded = again.get(f"/api/conversations/{conversation_id}")
    assert reloaded.json()["messages"][1]["content"] == "Hello"
    assert client.delete(f"/api/conversations/{conversation_id}").status_code == 200
    assert client.get(f"/api/conversations/{conversation_id}").status_code == 404


def test_thinking_is_stored_apart_from_the_answer(tmp_path, engine):
    state, base = engine
    state.reasoning_chunks = ["Count the sides. "]
    state.chunks = ["<think>square</think>", "Four sides."]
    client = _client(tmp_path)
    saved = _endpoint(client, base)
    created = client.post("/api/conversations", json={"endpoint_id": saved["id"], "model": "demo-text"})
    conversation_id = created.json()["id"]
    streamed = client.post("/api/chat", json={"conversation_id": conversation_id, "content": "How many sides?"})
    assert streamed.status_code == 200
    assert '"thinking": "Count the sides. "' in streamed.text
    assert '"thinking": "square"' in streamed.text
    assert '"delta": "Four sides."' in streamed.text
    assert "<think>" not in streamed.text
    loaded = client.get(f"/api/conversations/{conversation_id}")
    answer = loaded.json()["messages"][1]
    assert answer["content"] == "Four sides."
    assert answer["thinking"] == "Count the sides. square"


def test_whoami_is_the_local_session(tmp_path):
    client = _client(tmp_path)
    body = client.get("/api/whoami").json()
    assert body["session"] == "local"
    assert body["name"]
    assert body["host"]


def test_cloud_url_is_rejected_and_database_stays_empty(tmp_path):
    client = _client(tmp_path)
    response = client.post(
        "/api/endpoints",
        json={"name": "cloud", "base_url": "https://api.openai.com/v1", "kind": "openai"},
    )
    assert response.status_code == 400
    assert client.get("/api/endpoints").json()["endpoints"] == []


def test_private_network_requires_confirm(tmp_path):
    client = _client(tmp_path)
    raw = "http://192.168.1.20:11434/v1"
    denied = client.post(
        "/api/endpoints",
        json={"name": "lan", "base_url": raw, "kind": "ollama"},
    )
    assert denied.status_code == 400
    allowed = client.post(
        "/api/endpoints",
        json={"name": "lan", "base_url": raw, "kind": "ollama", "private_network_confirmed": True},
    )
    assert allowed.status_code == 201
    assert allowed.json()["private_network_confirmed"] is True


def test_health_reports_a_live_server_and_a_down_server(tmp_path, engine):
    _state, base = engine
    client = _client(tmp_path)
    saved = _endpoint(client, base)
    up = client.get("/api/health", params={"endpoint_id": saved["id"]})
    assert up.status_code == 200
    assert up.json()["ok"] is True
    assert up.json()["model_count"] == 1
    down = _endpoint(client, "http://127.0.0.1:1/v1", name="down")
    stopped = client.get("/api/health", params={"endpoint_id": down["id"]})
    assert stopped.status_code == 200
    assert stopped.json()["ok"] is False
