import json
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

PREVIEW_LIMIT = 240


class EngineError(RuntimeError):
    """The local model server failed or closed the stream early."""


@dataclass
class Speed:
    ttft_ms: int | None
    prompt_tokens: int | None
    output_tokens: int | None
    tokens_per_second: float | None
    total_ms: int
    text: str
    error: str | None


@dataclass
class StreamCapture:
    started: float = 0
    ended: float = 0
    first_token: float | None = None
    usage: dict | None = None
    content_chunks: int = 0
    error: str | None = None
    parts: list[str] | None = None

    def __post_init__(self) -> None:
        if self.parts is None:
            self.parts = []

    @property
    def text(self) -> str:
        return "".join(self.parts or [])

    def add_text(self, text: str, now: float) -> None:
        if not text:
            return
        if self.first_token is None:
            self.first_token = now
        self.content_chunks += 1
        self.parts.append(text)

    def finish(self) -> Speed:
        if self.ended <= 0:
            self.ended = time.perf_counter()
        return compute_speed(
            started=self.started,
            ended=self.ended,
            first_token=self.first_token,
            content_chunks=self.content_chunks,
            usage=self.usage,
            text=self.text,
            error=self.error,
        )


def compute_speed(
    *,
    started: float,
    ended: float,
    first_token: float | None,
    content_chunks: int,
    usage: dict | None,
    text: str,
    error: str | None = None,
) -> Speed:
    total_ms = max(0, int(round((ended - started) * 1000)))
    ttft_ms = None if first_token is None else max(0, int(round((first_token - started) * 1000)))
    prompt_tokens = None
    output_tokens = None
    if usage is not None and usage.get("completion_tokens") is not None:
        output_tokens = int(usage["completion_tokens"])
        if usage.get("prompt_tokens") is not None:
            prompt_tokens = int(usage["prompt_tokens"])
    elif content_chunks > 0:
        output_tokens = content_chunks
    resolved_error = error
    if first_token is None and not resolved_error:
        resolved_error = "The stream closed before any token."
    tokens_per_second = None
    if resolved_error is None and output_tokens is not None and total_ms > 0:
        tokens_per_second = output_tokens / (total_ms / 1000)
    return Speed(
        ttft_ms=ttft_ms if resolved_error is None or first_token is not None else None,
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        tokens_per_second=tokens_per_second,
        total_ms=total_ms,
        text=text,
        error=resolved_error,
    )


def measure_lines(lines: list[tuple[float, str]], *, started_at: float, ended_at: float) -> Speed:
    capture = StreamCapture(started=started_at)
    for stamp, line in lines:
        payload = parse_sse_data(line)
        if payload is None:
            continue
        if payload.get("done"):
            continue
        _apply_payload(capture, payload, stamp)
    capture.ended = ended_at
    return capture.finish()


def parse_sse_data(line: str) -> dict | None:
    stripped = line.strip()
    if stripped.startswith("data:"):
        data = stripped[5:].strip()
    elif stripped.startswith("{") or stripped.startswith("["):
        data = stripped
    else:
        return None
    if not data:
        return None
    if data == "[DONE]":
        return {"done": True}
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def origin_of(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def auth_headers(api_key: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def list_model_ids(base_url: str, api_key: str | None = None, timeout: float = 10) -> list[str]:
    url = base_url.rstrip("/") + "/models"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=auth_headers(api_key))
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise EngineError(str(exc)) from exc
    return model_ids_from_payload(payload)


def model_ids_from_payload(payload: Any) -> list[str]:
    items = []
    if isinstance(payload, dict):
        items = payload.get("data") or payload.get("models") or []
    ids: list[str] = []
    for item in items:
        if isinstance(item, str):
            ids.append(item)
        elif isinstance(item, dict):
            model_id = item.get("id") or item.get("name")
            if model_id:
                ids.append(str(model_id))
    return ids


def build_messages(content: str, image_data_url: str | None, history: list[dict] | None = None) -> list[dict]:
    messages: list[dict] = []
    for turn in history or []:
        if turn.get("error"):
            continue
        messages.append({"role": turn["role"], "content": turn["content"]})
    if image_data_url:
        user_content: str | list[dict] = [
            {"type": "text", "text": content},
            {"type": "image_url", "image_url": {"url": image_data_url}},
        ]
    else:
        user_content = content
    messages.append({"role": "user", "content": user_content})
    return messages


def iter_chat_deltas(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
    messages: list[dict],
    capture: StreamCapture,
    timeout: float = 300,
) -> Iterator[tuple[str, str]]:
    body = {
        "model": model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    url = base_url.rstrip("/") + "/chat/completions"
    capture.started = time.perf_counter()
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
            with client.stream("POST", url, json=body, headers=auth_headers(api_key)) as response:
                if response.status_code >= 400:
                    detail = response.read().decode("utf-8", errors="replace")
                    capture.error = _http_error(response.status_code, detail)
                    capture.ended = time.perf_counter()
                    return
                for line in response.iter_lines():
                    payload = parse_sse_data(line)
                    if payload is None or payload.get("done"):
                        continue
                    if payload.get("error"):
                        capture.error = _error_message(payload["error"])
                        break
                    text = delta_text(payload)
                    thinking = delta_thinking(payload)
                    now = time.perf_counter()
                    usage = payload.get("usage")
                    if isinstance(usage, dict) and usage.get("completion_tokens") is not None:
                        capture.usage = usage
                    if thinking:
                        yield ("thinking", thinking)
                    if text:
                        capture.add_text(text, now)
                        yield ("content", text)
    except httpx.HTTPError as exc:
        capture.error = str(exc)
    capture.ended = time.perf_counter()


def stream_chat(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
    messages: list[dict],
    on_delta: Callable[[str], None] | None = None,
    timeout: float = 300,
) -> Speed:
    capture = StreamCapture()
    for kind, delta in iter_chat_deltas(
        base_url=base_url,
        api_key=api_key,
        model=model,
        messages=messages,
        capture=capture,
        timeout=timeout,
    ):
        if kind == "content" and on_delta is not None:
            on_delta(delta)
    return capture.finish()


def delta_text(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    delta = choices[0].get("delta") or choices[0].get("message") or {}
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "".join(parts)
    return ""


def delta_thinking(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    delta = choices[0].get("delta") or choices[0].get("message") or {}
    if not isinstance(delta, dict):
        return ""
    for key in ("reasoning_content", "reasoning", "thinking"):
        value = delta.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


_OPEN_TAGS = ("<think>", "<thinking>")
_CLOSE_TAGS = ("</think>", "</thinking>")


class ThinkSplitter:
    """Pull <think> blocks out of a content stream without counting them as the answer."""

    def __init__(self) -> None:
        self._buffer = ""
        self._inside = False

    def feed(self, text: str) -> list[tuple[str, str]]:
        self._buffer += text
        pieces: list[tuple[str, str]] = []
        while self._buffer:
            tags = _CLOSE_TAGS if self._inside else _OPEN_TAGS
            kind = "thinking" if self._inside else "content"
            at, length = _first_tag(self._buffer.lower(), tags)
            if at == -1:
                hold = _held_prefix(self._buffer, tags)
                emit = self._buffer[:-hold] if hold else self._buffer
                self._buffer = self._buffer[-hold:] if hold else ""
                if emit:
                    pieces.append((kind, emit))
                break
            if at:
                pieces.append((kind, self._buffer[:at]))
            self._buffer = self._buffer[at + length :]
            self._inside = not self._inside
        return pieces

    def finish(self) -> list[tuple[str, str]]:
        if not self._buffer:
            return []
        kind = "thinking" if self._inside else "content"
        text = self._buffer
        self._buffer = ""
        return [(kind, text)]


def _first_tag(lower: str, tags: tuple[str, ...]) -> tuple[int, int]:
    found = -1
    length = 0
    for tag in tags:
        at = lower.find(tag)
        if at != -1 and (found == -1 or at < found):
            found = at
            length = len(tag)
    return found, length


def _held_prefix(text: str, tags: tuple[str, ...]) -> int:
    lower = text.lower()
    best = 0
    for tag in tags:
        limit = min(len(tag) - 1, len(lower))
        for size in range(1, limit + 1):
            if lower.endswith(tag[:size]):
                best = max(best, size)
    return best


def preview(text: str) -> str:
    if len(text) <= PREVIEW_LIMIT:
        return text
    return text[: PREVIEW_LIMIT - 1] + "…"


def _apply_payload(capture: StreamCapture, payload: dict, stamp: float) -> None:
    if payload.get("error"):
        capture.error = _error_message(payload["error"])
        return
    usage = payload.get("usage")
    if isinstance(usage, dict) and usage.get("completion_tokens") is not None:
        capture.usage = usage
    capture.add_text(delta_text(payload), stamp)


def _error_message(error: Any) -> str:
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error)


def _http_error(status: int, detail: str) -> str:
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        if isinstance(payload.get("error"), dict) and payload["error"].get("message"):
            return str(payload["error"]["message"])
        if payload.get("error"):
            return _error_message(payload["error"])
    text = detail.strip() or f"The model server returned HTTP {status}."
    return text[:500]
