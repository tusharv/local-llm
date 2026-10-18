import json
from collections.abc import Iterator
from urllib.parse import urlparse, urlunparse

import httpx

from studio.engines.openai_compatible import EngineError, auth_headers, origin_of

VISION_FAMILIES = (
    "llava",
    "bakllava",
    "moondream",
    "minicpm-v",
    "qwen2-vl",
    "qwen2.5vl",
    "qwen2.5-vl",
    "qwen3-vl",
    "llama3.2-vision",
    "pixtral",
    "internvl",
    "cogvlm",
    "yi-vl",
    "granite-vision",
    "mllama",
)


def effective_vision(endpoint: dict, model: str, flag: dict | None) -> tuple[bool, str]:
    override = flag.get("vision_override") if flag else None
    probe = flag.get("probe_result") if flag else None
    capabilities = None
    family = None
    if override not in {"on", "off"} and endpoint.get("kind") == "ollama":
        try:
            capabilities, family, _size = parse_show(
                show_model(endpoint["base_url"], model, endpoint.get("api_key"))
            )
        except EngineError:
            capabilities = None
    return resolve_vision(
        override=override,
        capabilities=capabilities,
        family=family,
        model_name=model,
        probe=probe,
    )


def resolve_vision(
    *,
    override: str | None,
    capabilities: list[str] | None,
    family: str | None,
    model_name: str,
    probe: str | None,
) -> tuple[bool, str]:
    if override == "on":
        return True, "override"
    if override == "off":
        return False, "override"
    if capabilities is not None:
        names = {str(item).lower() for item in capabilities}
        return ("vision" in names), "capabilities"
    if _family_match(family, model_name):
        return True, "family"
    if probe == "vision":
        return True, "probe"
    if probe == "text":
        return False, "probe"
    return False, "unknown"


def parse_show(payload: dict) -> tuple[list[str] | None, str | None, int | None]:
    if "capabilities" in payload and payload.get("capabilities") is not None:
        capabilities = [str(item) for item in payload["capabilities"]]
    else:
        capabilities = None
    details = payload.get("details") or {}
    family = details.get("family")
    if family is not None:
        family = str(family)
    size = payload.get("size")
    size_bytes = int(size) if isinstance(size, int) else None
    return capabilities, family, size_bytes


def show_model(base_url: str, model: str, api_key: str | None = None, timeout: float = 10) -> dict:
    last_error: Exception | None = None
    for native in native_roots(base_url):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    native + "/api/show",
                    json={"name": model},
                    headers=auth_headers(api_key),
                )
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            last_error = exc
    if last_error is not None:
        raise EngineError(str(last_error))
    raise EngineError("Ollama model details were not available.")


def iter_pull(
    base_url: str, name: str, api_key: str | None = None, timeout: float = 3600
) -> Iterator[dict]:
    native = origin_of(base_url)
    with httpx.Client(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
        with client.stream(
            "POST",
            native + "/api/pull",
            json={"name": name, "stream": True},
            headers=auth_headers(api_key),
        ) as response:
            if response.status_code >= 400:
                detail = response.read().decode("utf-8", errors="replace")
                raise EngineError(detail.strip() or f"Ollama pull failed with HTTP {response.status_code}.")
            for line in response.iter_lines():
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    if payload.get("error"):
                        raise EngineError(str(payload["error"]))
                    yield {
                        "status": str(payload.get("status") or ""),
                        "completed": payload.get("completed"),
                        "total": payload.get("total"),
                    }


def delete_model(base_url: str, name: str, api_key: str | None = None, timeout: float = 60) -> None:
    native = origin_of(base_url)
    with httpx.Client(timeout=timeout) as client:
        response = client.request(
            "DELETE",
            native + "/api/delete",
            json={"name": name},
            headers=auth_headers(api_key),
        )
        if response.status_code >= 400:
            raise EngineError(response.text.strip() or f"Ollama delete failed with HTTP {response.status_code}.")


def native_roots(base_url: str) -> list[str]:
    origin = origin_of(base_url)
    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    ported = urlunparse((parsed.scheme, f"{host}:11434", "", "", "", ""))
    roots = [origin]
    if ported != origin:
        roots.append(ported)
    return roots


def _family_match(family: str | None, model_name: str) -> bool:
    haystack = f"{family or ''} {model_name}".lower()
    return any(token in haystack for token in VISION_FAMILIES)
