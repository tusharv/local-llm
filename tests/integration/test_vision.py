from fastapi.testclient import TestClient

from studio.main import create_app

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0P"
    b"\x0f\x00\x04\x85\x01\x80\x84\xa9\x8c!\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _client(tmp_path):
    return TestClient(create_app(tmp_path))


def _prepare(client, base, model="demo-text"):
    saved = client.post(
        "/api/endpoints",
        json={"name": "local", "base_url": base, "kind": "openai"},
    )
    assert saved.status_code == 201, saved.text
    endpoint_id = saved.json()["id"]
    created = client.post(
        "/api/conversations",
        json={"endpoint_id": endpoint_id, "model": model},
    )
    assert created.status_code == 201, created.text
    return endpoint_id, created.json()["id"]


def test_image_is_stored_and_sent_as_a_data_url(tmp_path, engine):
    state, base = engine
    state.chunks = ["a red square"]
    client = _client(tmp_path)
    endpoint_id, conversation_id = _prepare(client, base)
    flagged = client.put(
        "/api/models/flags",
        json={"endpoint_id": endpoint_id, "model": "demo-text", "vision_override": "on"},
    )
    assert flagged.status_code == 200
    response = client.post(
        "/api/chat",
        data={"conversation_id": str(conversation_id), "content": "What is this?"},
        files={"image": ("shapes.png", PNG, "image/png")},
    )
    assert response.status_code == 200, response.text
    sent = state.chat_requests[-1]["messages"][-1]["content"]
    assert any(part.get("type") == "image_url" and part["image_url"]["url"].startswith("data:image/png;base64,") for part in sent)
    uploads = list((tmp_path / "uploads").iterdir())
    assert len(uploads) == 1
    loaded = client.get(f"/api/conversations/{conversation_id}").json()
    assert loaded["messages"][0]["image_url"].startswith("/uploads/")
    assert client.delete(f"/api/conversations/{conversation_id}").status_code == 200
    assert list((tmp_path / "uploads").iterdir()) == []


def test_text_model_rejects_an_image_before_the_engine_call(tmp_path, engine):
    state, base = engine
    client = _client(tmp_path)
    _endpoint_id, conversation_id = _prepare(client, base)
    response = client.post(
        "/api/chat",
        data={"conversation_id": str(conversation_id), "content": "Look"},
        files={"image": ("shapes.png", PNG, "image/png")},
    )
    assert response.status_code == 400
    assert state.chat_requests == []
    assert list((tmp_path / "uploads").iterdir()) == []


def test_vision_check_caches_probe(tmp_path, engine):
    state, base = engine
    state.models = ["demo-text"]
    state.chunks = ["red square, blue rectangle, green triangle"]
    client = _client(tmp_path)
    endpoint_id, _conversation_id = _prepare(client, base)
    checked = client.post("/api/vision-check", json={"endpoint_id": endpoint_id, "model": "demo-text"})
    assert checked.status_code == 200, checked.text
    body = checked.json()
    assert body["vision"] is True
    assert "red square" in body["answer"]
    assert body["ttft_ms"] is not None
    assert body["total_ms"] is not None
    listed = client.get("/api/models", params={"endpoint_id": endpoint_id})
    assert listed.json()["models"][0]["vision"] is True
    assert listed.json()["models"][0]["vision_source"] == "probe"
    state.chat_error = "This model cannot read images."
    state.chunks = []
    failed = client.post("/api/vision-check", json={"endpoint_id": endpoint_id, "model": "demo-text"})
    assert failed.status_code == 200
    assert failed.json()["vision"] is False
    listed_again = client.get("/api/models", params={"endpoint_id": endpoint_id})
    assert listed_again.json()["models"][0]["vision_source"] == "probe"
    assert listed_again.json()["models"][0]["vision"] is False
