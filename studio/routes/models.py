import base64
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from studio.assets import IMAGE_PATH, QUESTION
from studio.db import connect, get_endpoint, get_model_flag, set_probe_result, set_vision_override
from studio.engines.ollama import (
    EngineError,
    delete_model,
    effective_vision,
    iter_pull,
    parse_show,
    resolve_vision,
    show_model,
)
from studio.engines.openai_compatible import build_messages, list_model_ids, stream_chat
from studio.routes import error

router = APIRouter()


class FlagIn(BaseModel):
    endpoint_id: int
    model: str
    vision_override: str | None = None


class PullIn(BaseModel):
    endpoint_id: int
    name: str


class VisionCheckIn(BaseModel):
    endpoint_id: int
    model: str


@router.get("/api/models")
def get_models(endpoint_id: int, request: Request):
    with connect(request.app.state.db_path) as conn:
        endpoint = get_endpoint(conn, endpoint_id)
        if endpoint is None:
            return error("Endpoint not found.", 404)
    try:
        model_ids = list_model_ids(endpoint["base_url"], endpoint.get("api_key"))
    except EngineError as exc:
        return error(str(exc), 502)
    models = []
    with connect(request.app.state.db_path) as conn:
        for model_id in model_ids:
            flag = get_model_flag(conn, endpoint_id, model_id)
            item = _model_item(endpoint, model_id, flag)
            models.append(item)
    return {"models": models}


@router.put("/api/models/flags")
def put_flag(body: FlagIn, request: Request):
    if body.vision_override not in {None, "on", "off"}:
        return error("vision_override must be on, off, or null.", 400)
    with connect(request.app.state.db_path) as conn:
        endpoint = get_endpoint(conn, body.endpoint_id)
        if endpoint is None:
            return error("Endpoint not found.", 404)
        flag = set_vision_override(
            conn,
            endpoint_id=body.endpoint_id,
            model=body.model,
            vision_override=body.vision_override,
        )
    vision, source = _vision(endpoint, body.model, flag)
    return {"vision": vision, "vision_source": source, "model": body.model}


@router.post("/api/models/pull")
def pull_model(body: PullIn, request: Request):
    with connect(request.app.state.db_path) as conn:
        endpoint = get_endpoint(conn, body.endpoint_id)
    if endpoint is None:
        return error("Endpoint not found.", 404)
    if endpoint["kind"] != "ollama":
        return error("Pull is only available for an Ollama server. Load the model in that runtime, then refresh.", 400)
    name = body.name.strip()
    if not name:
        return error("A model name is required.", 400)

    def generate():
        try:
            for event in iter_pull(endpoint["base_url"], name, endpoint.get("api_key")):
                yield _sse(event)
            yield _sse({"done": True})
        except EngineError as exc:
            yield _sse({"error": str(exc)})

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/api/model-pulls")
def pull_status(endpoint_id: int, request: Request):
    return {"job": request.app.state.pulls.get(endpoint_id)}


@router.post("/api/model-pulls", status_code=202)
def start_pull(body: PullIn, request: Request):
    with connect(request.app.state.db_path) as conn:
        endpoint = get_endpoint(conn, body.endpoint_id)
    if not endpoint:
        return error("Endpoint not found.", 404)
    if endpoint["kind"] != "ollama":
        return error("Downloads are only available for Ollama servers.", 400)
    if not body.name.strip():
        return error("A model name is required.", 400)
    try:
        return {"job": request.app.state.pulls.start(endpoint, body.name.strip())}
    except ValueError as exc:
        return error(str(exc), 409)


@router.delete("/api/models/{model_name:path}")
def remove_model(model_name: str, endpoint_id: int, request: Request):
    with connect(request.app.state.db_path) as conn:
        endpoint = get_endpoint(conn, endpoint_id)
    if endpoint is None:
        return error("Endpoint not found.", 404)
    if endpoint["kind"] != "ollama":
        return error("Delete is only available for an Ollama server. Remove the model in that runtime, then refresh.", 400)
    try:
        delete_model(endpoint["base_url"], model_name, endpoint.get("api_key"))
    except EngineError as exc:
        return error(str(exc), 502)
    return {"ok": True}


@router.post("/api/vision-check")
def vision_check(body: VisionCheckIn, request: Request):
    with connect(request.app.state.db_path) as conn:
        endpoint = get_endpoint(conn, body.endpoint_id)
    if endpoint is None:
        return error("Endpoint not found.", 404)
    if not IMAGE_PATH.is_file():
        return error("The bundled vision image is missing.", 500)
    raw = IMAGE_PATH.read_bytes()
    data_url = "data:image/png;base64," + base64.standard_b64encode(raw).decode("ascii")
    speed = stream_chat(
        base_url=endpoint["base_url"],
        api_key=endpoint.get("api_key"),
        model=body.model,
        messages=build_messages(QUESTION, data_url),
    )
    if speed.error or not speed.text.strip():
        probe = "text"
        vision = False
        answer = speed.error or "The model returned no description of the image."
    else:
        probe = "vision"
        vision = True
        answer = speed.text
    with connect(request.app.state.db_path) as conn:
        set_probe_result(conn, endpoint_id=body.endpoint_id, model=body.model, probe_result=probe)
    return {
        "answer": answer,
        "ttft_ms": speed.ttft_ms,
        "total_ms": speed.total_ms,
        "vision": vision,
    }


def _model_item(endpoint: dict, model_id: str, flag: dict | None) -> dict:
    capabilities = None
    family = None
    size_bytes = None
    if endpoint["kind"] == "ollama":
        try:
            capabilities, family, size_bytes = parse_show(
                show_model(endpoint["base_url"], model_id, endpoint.get("api_key"))
            )
        except EngineError:
            capabilities = None
    override = flag.get("vision_override") if flag else None
    probe = flag.get("probe_result") if flag else None
    vision, source = resolve_vision(
        override=override,
        capabilities=capabilities,
        family=family,
        model_name=model_id,
        probe=probe,
    )
    item = {"id": model_id, "vision": vision, "vision_source": source}
    if family:
        item["family"] = family
    if size_bytes is not None:
        item["size_bytes"] = size_bytes
    return item


def _vision(endpoint: dict, model: str, flag: dict | None) -> tuple[bool, str]:
    return effective_vision(endpoint, model, flag)


def _sse(payload: dict) -> str:
    return "data: " + json.dumps(payload) + "\n\n"
