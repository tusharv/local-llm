from urllib.parse import urlparse

from fastapi import APIRouter, Request
from pydantic import BaseModel

from studio.db import connect, create_endpoint, delete_endpoint, get_endpoint, list_endpoints, public_endpoint
from studio.routes import error
from studio.url_policy import UrlPolicyError, accept_base_url, host_class

router = APIRouter()


class EndpointIn(BaseModel):
    name: str
    base_url: str
    kind: str
    api_key: str | None = None
    private_network_confirmed: bool = False


@router.get("/api/endpoints")
def get_endpoints(request: Request):
    with connect(request.app.state.db_path) as conn:
        return {"endpoints": list_endpoints(conn)}


@router.post("/api/endpoints", status_code=201)
def post_endpoint(body: EndpointIn, request: Request):
    name = body.name.strip()
    if not name:
        return error("A name is required.", 400)
    if body.kind not in {"openai", "ollama"}:
        return error("kind must be openai or ollama.", 400)
    try:
        base_url = accept_base_url(body.base_url, body.private_network_confirmed)
    except UrlPolicyError as exc:
        return error(str(exc), 400)
    confirmed = host_class(urlparse(base_url).hostname or "") == "private"
    api_key = body.api_key.strip() if body.api_key else None
    with connect(request.app.state.db_path) as conn:
        row = create_endpoint(
            conn,
            name=name,
            base_url=base_url,
            kind=body.kind,
            api_key=api_key or None,
            private_network_confirmed=confirmed,
        )
    return public_endpoint(row)


@router.delete("/api/endpoints/{endpoint_id}")
def remove_endpoint(endpoint_id: int, request: Request):
    with connect(request.app.state.db_path) as conn:
        if not get_endpoint(conn, endpoint_id):
            return error("Endpoint not found.", 404)
        delete_endpoint(conn, endpoint_id)
    return {"ok": True}
