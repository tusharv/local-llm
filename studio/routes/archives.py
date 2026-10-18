"""Portable conversation backups. Server credentials and internal IDs are excluded."""
import base64
import json
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError
from studio.db import connect, get_conversation, get_endpoint, create_conversation, add_message
from studio.routes import error

router = APIRouter()

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=1_000_000)
    thinking: str | None = Field(default=None, max_length=1_000_000)
    error: str | None = Field(default=None, max_length=10000)
    image: str | None = None

class Chat(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=200)
    messages: list[Message] = Field(max_length=10000)

class Archive(BaseModel):
    format: Literal["local-llm-studio"]
    version: Literal[1]
    conversations: list[Chat] = Field(min_length=1, max_length=1000)

@router.get("/api/conversation-archive/{public_id}")
def export_chat(public_id: str, request: Request):
    with connect(request.app.state.db_path) as conn:
        found = conn.execute("SELECT id FROM conversation WHERE public_id=?", (public_id,)).fetchone()
        if not found:
            return error("Conversation not found.", 404)
        chat = get_conversation(conn, found[0])
    messages = []
    for message in chat["messages"]:
        item = {key: message[key] for key in ("role", "content", "thinking", "error")}
        if message.get("image_path"):
            path = Path(message["image_path"]).resolve()
            if path.parent != request.app.state.uploads_dir.resolve() or not path.is_file():
                return error("An attachment is missing. The conversation cannot be fully exported.", 409)
            item["image"] = base64.b64encode(path.read_bytes()).decode()
        messages.append(item)
    payload = {"format":"local-llm-studio", "version":1, "conversations":[{"title":chat["title"], "model":chat["model"], "messages":messages}]}
    return Response(json.dumps(payload, ensure_ascii=False, indent=2), media_type="application/json", headers={"Content-Disposition":f'attachment; filename="chat-{public_id}.json"'})

@router.post("/api/conversation-archive", status_code=201)
async def import_chats(endpoint_id: int, request: Request):
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 20 * 1024 * 1024:
            return error("This backup exceeds the 20 MB import limit.", 413)
    try:
        archive = Archive.model_validate_json(bytes(raw))
        decoded = []
        for chat in archive.conversations:
            for message in chat.messages:
                if message.image:
                    data = base64.b64decode(message.image, validate=True)
                    if len(data) > 10 * 1024 * 1024:
                        raise ValueError("Attachment too large")
                    ext = ".png" if data.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg" if data.startswith(b"\xff\xd8\xff") else ".gif" if data.startswith((b"GIF87a", b"GIF89a")) else ".webp" if data[:4] == b"RIFF" and data[8:12] == b"WEBP" else None
                    if not ext:
                        raise ValueError("Unsupported image")
                    decoded.append((data, ext))
                else:
                    decoded.append(None)
    except (ValidationError, ValueError, TypeError):
        return error("Invalid Studio backup. Choose an exported conversation JSON file with supported image attachments.", 400)
    paths = []
    imported = []
    images = iter(decoded)
    try:
        with connect(request.app.state.db_path) as conn:
            if not get_endpoint(conn, endpoint_id):
                return error("Choose a saved server before importing.", 400)
            for chat in archive.conversations:
                row = create_conversation(conn, endpoint_id=endpoint_id, model=chat.model, title=chat.title)
                for message in chat.messages:
                    image = next(images)
                    path = None
                    if image:
                        path = request.app.state.uploads_dir / (uuid.uuid4().hex + image[1])
                        paths.append(path)
                        path.write_bytes(image[0])
                    add_message(conn, conversation_id=row["id"], role=message.role, content=message.content, thinking=message.thinking, error=message.error, image_path=str(path) if path else None)
                row.pop("messages", None)
                imported.append(row)
    except Exception:
        for path in paths:
            path.unlink(missing_ok=True)
        raise
    return {"conversations": imported}
