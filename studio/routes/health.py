import getpass
import socket

from fastapi import APIRouter, Request

from studio.db import connect, get_endpoint
from studio.engines.openai_compatible import EngineError, list_model_ids
from studio.routes import error

router = APIRouter()


@router.get("/api/whoami")
def whoami():
    try:
        name = getpass.getuser() or "local"
    except Exception:
        name = "local"
    try:
        host = socket.gethostname() or "this computer"
    except Exception:
        host = "this computer"
    return {"name": name, "host": host, "session": "local"}


@router.get("/api/health")
def health(endpoint_id: int, request: Request):
    with connect(request.app.state.db_path) as conn:
        endpoint = get_endpoint(conn, endpoint_id)
    if endpoint is None:
        return error("Endpoint not found.", 404)
    try:
        models = list_model_ids(endpoint["base_url"], endpoint.get("api_key"), timeout=3)
    except EngineError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "model_count": len(models)}
