import base64
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from studio.db import add_message, connect, get_conversation, get_endpoint, get_model_flag, touch_conversation
from studio.engines.ollama import effective_vision
from studio.engines.openai_compatible import StreamCapture, ThinkSplitter, build_messages, iter_chat_deltas
from studio.routes import error

router = APIRouter()

IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


@router.get("/api/conversations")
def get_conversations(request: Request):
    from studio.db import list_conversations

    with connect(request.app.state.db_path) as conn:
        return {"conversations": list_conversations(conn)}


@router.post("/api/conversations", status_code=201)
async def post_conversation(request: Request):
    from studio.db import create_conversation

    body = await request.json()
    endpoint_id = body.get("endpoint_id")
    model = (body.get("model") or "").strip()
    if not endpoint_id or not model:
        return error("endpoint_id and model are required.", 400)
    title = (body.get("title") or "New chat").strip()[:80] or "New chat"
    with connect(request.app.state.db_path) as conn:
        endpoint = get_endpoint(conn, int(endpoint_id))
        if endpoint is None:
            return error("Endpoint not found.", 404)
        row = create_conversation(conn, endpoint_id=int(endpoint_id), model=model, title=title)
    row.pop("messages", None)
    return row


@router.get("/api/conversations/{conversation_id}")
def get_one_conversation(conversation_id: str, request: Request):
    with connect(request.app.state.db_path) as conn:
        if conversation_id.isdecimal():
            internal_id = int(conversation_id)
        else:
            found = conn.execute("SELECT id FROM conversation WHERE public_id=?", (conversation_id,)).fetchone()
            internal_id = found[0] if found else -1
        row = get_conversation(conn, internal_id)
    if row is None:
        return error("Conversation not found.", 404)
    row["messages"] = [_present_message(message) for message in row["messages"]]
    return row


@router.delete("/api/conversations/{conversation_id}")
def remove_conversation(conversation_id: int, request: Request):
    from studio.db import delete_conversation

    with connect(request.app.state.db_path) as conn:
        paths = delete_conversation(conn, conversation_id)
    if paths is None:
        return error("Conversation not found.", 404)
    _remove_images(request.app.state.data_dir, paths)
    return {"ok": True}


@router.post("/api/chat")
async def post_chat(request: Request):
    content_type = request.headers.get("content-type", "")
    upload_name = None
    upload_bytes = None
    upload_type = None
    if "multipart/form-data" in content_type:
        form = await request.form()
        conversation_id = form.get("conversation_id")
        content = str(form.get("content") or "")
        upload = form.get("image")
        if upload is not None and hasattr(upload, "read"):
            upload_type = getattr(upload, "content_type", None) or "application/octet-stream"
            upload_bytes = await upload.read()
            upload_name = getattr(upload, "filename", None) or "image"
    else:
        body = await request.json()
        conversation_id = body.get("conversation_id")
        content = str(body.get("content") or "")
    if not conversation_id:
        return error("conversation_id is required.", 400)
    conversation_id = int(conversation_id)
    with connect(request.app.state.db_path) as conn:
        conversation = get_conversation(conn, conversation_id)
        if conversation is None:
            return error("Conversation not found.", 404)
        endpoint = get_endpoint(conn, conversation["endpoint_id"])
        if endpoint is None:
            return error("That conversation's server is no longer saved.", 404)
        flag = get_model_flag(conn, endpoint["id"], conversation["model"])
        prior = [dict(message) for message in conversation["messages"]]
    vision, _source = effective_vision(endpoint, conversation["model"], flag)
    if upload_bytes is not None and not vision:
        return error("This model is not marked as able to see images.", 400)
    if upload_bytes is not None and upload_type not in IMAGE_TYPES:
        return error("Attach a PNG, JPEG, GIF, or WebP image.", 400)
    if upload_bytes is not None and len(upload_bytes) > MAX_IMAGE_BYTES:
        return error("That image is larger than 10 MB.", 400)
    relative = None
    data_url = None
    if upload_bytes is not None:
        filename = uuid.uuid4().hex + IMAGE_TYPES[upload_type]
        path = request.app.state.uploads_dir / filename
        path.write_bytes(upload_bytes)
        relative = f"uploads/{filename}"
        data_url = "data:" + upload_type + ";base64," + base64.standard_b64encode(upload_bytes).decode("ascii")
    title = None
    if conversation["title"] == "New chat" and content.strip():
        title = content.strip()[:80]
    with connect(request.app.state.db_path) as conn:
        add_message(
            conn,
            conversation_id=conversation_id,
            role="user",
            content=content,
            image_path=relative,
        )
        touch_conversation(conn, conversation_id, title)

    def generate():
        capture = StreamCapture()
        splitter = ThinkSplitter()
        visible: list[str] = []
        thoughts: list[str] = []

        def take(kind: str, piece: str):
            if not piece:
                return None
            if kind == "thinking":
                thoughts.append(piece)
                return _sse({"thinking": piece})
            visible.append(piece)
            return _sse({"delta": piece})

        try:
            for kind, piece in iter_chat_deltas(
                base_url=endpoint["base_url"],
                api_key=endpoint.get("api_key"),
                model=conversation["model"],
                messages=build_messages(content, data_url, history=prior),
                capture=capture,
            ):
                if kind == "thinking":
                    event = take("thinking", piece)
                    if event:
                        yield event
                    continue
                for part_kind, part in splitter.feed(piece):
                    event = take(part_kind, part)
                    if event:
                        yield event
            for part_kind, part in splitter.finish():
                event = take(part_kind, part)
                if event:
                    yield event
            speed = capture.finish()
            thinking = "".join(thoughts) or None
            with connect(request.app.state.db_path) as conn:
                saved = add_message(
                    conn,
                    conversation_id=conversation_id,
                    role="assistant",
                    content="".join(visible),
                    error=speed.error,
                    thinking=thinking,
                )
                touch_conversation(conn, conversation_id)
            if speed.error:
                yield _sse({"error": speed.error, "message_id": saved["id"]})
            else:
                yield _sse({"done": True, "message_id": saved["id"]})
        except Exception as exc:
            with connect(request.app.state.db_path) as conn:
                add_message(
                    conn,
                    conversation_id=conversation_id,
                    role="assistant",
                    content="",
                    error=str(exc),
                )
            yield _sse({"error": str(exc)})

    return StreamingResponse(generate(), media_type="text/event-stream")


def _present_message(message: dict) -> dict:
    item = {
        "id": message["id"],
        "role": message["role"],
        "content": message["content"],
        "thinking": message.get("thinking") or None,
        "error": message["error"],
        "created_at": message["created_at"],
    }
    if message.get("image_path"):
        item["image_url"] = "/uploads/" + Path(message["image_path"]).name
    return item


def _remove_images(data_dir: Path, relative_paths: list[str]) -> None:
    root = (data_dir / "uploads").resolve()
    for relative in relative_paths:
        path = (data_dir / relative).resolve()
        if path.parent == root and path.is_file():
            path.unlink()


def _sse(payload: dict) -> str:
    return "data: " + json.dumps(payload) + "\n\n"
