"""Optional image generation through the saved local OpenAI-compatible server."""
import base64
import binascii
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx

from studio.engines.openai_compatible import EngineError, auth_headers

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 12 * 1024 * 1024


def decode_image(payload: dict) -> tuple[bytes, str]:
    data = payload.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise EngineError("The image server returned no image data.")
    encoded = data[0].get("b64_json")
    if not isinstance(encoded, str):
        raise EngineError("This server must return base64 image data (b64_json). Image URLs are not downloaded.")
    if len(encoded) > MAX_IMAGE_BYTES * 4 // 3 + 4:
        raise EngineError("The generated image exceeds the 8 MB limit.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EngineError("The image server returned invalid base64 data.") from exc
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = "png"
    elif raw.startswith(b"\xff\xd8\xff"):
        extension = "jpg"
    elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        extension = "webp"
    else:
        raise EngineError("The image server must return a PNG, JPEG, or WebP image.")
    return raw, extension


def generate_image(endpoint: dict, model: str, prompt: str, uploads_dir: Path) -> dict:
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=httpx.Timeout(180, connect=5), follow_redirects=False) as client:
            with client.stream("POST", endpoint["base_url"].rstrip("/") + "/images/generations",
                               headers=auth_headers(endpoint.get("api_key")),
                               json={"model": model, "prompt": prompt, "n": 1, "size": "512x512", "response_format": "b64_json"}) as response:
                if response.status_code in (404, 405, 501):
                    raise EngineError("This server does not support image generation at /v1/images/generations. Choose an image-generation server and model.")
                if not response.is_success:
                    raise EngineError(f"Image generation failed (HTTP {response.status_code}). Check the model name and server image settings.")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise EngineError("The image response is too large (12 MB maximum).")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise EngineError("The image server returned an invalid response.")
        image, extension = decode_image(payload)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        name = f"benchmark-{uuid4().hex}.{extension}"
        (uploads_dir / name).write_bytes(image)
        return {"image_path": name, "total_ms": round((time.perf_counter() - started) * 1000), "error": None}
    except (httpx.HTTPError, ValueError, EngineError, OSError) as exc:
        return {"image_path": None, "total_ms": round((time.perf_counter() - started) * 1000), "error": str(exc)}
