import base64
import threading
from collections.abc import Iterator

from studio.assets import IMAGE_PATH
from studio.benchmarks.suite import SUITE_VERSION, cases_for
from studio.db import (
    add_benchmark_result,
    connect,
    create_benchmark_run,
    finish_benchmark_run,
    has_running_benchmark,
)
from studio.engines.openai_compatible import build_messages, preview, stream_chat

_run_lock = threading.Lock()


class BenchmarkBusy(RuntimeError):
    """Another benchmark is still running."""


def start_run_row(db_path, endpoint: dict, model: str, warmup: bool, repeat_count: int) -> dict:
    with _run_lock:
        with connect(db_path) as conn:
            if has_running_benchmark(conn):
                raise BenchmarkBusy("A benchmark is already running.")
            return create_benchmark_run(
                conn,
                endpoint_id=endpoint["id"],
                endpoint_kind=endpoint["kind"],
                model=model,
                suite_version=SUITE_VERSION,
                warmup=warmup,
                repeat_count=repeat_count,
            )


def iter_run(
    *,
    db_path,
    endpoint: dict,
    model: str,
    vision: bool,
    warmup: bool,
    repeat_count: int,
    run_id: int,
) -> Iterator[dict]:
    status = "done"
    try:
        if warmup:
            _ask(endpoint, model, "Reply with one word: hello.", image=None)
            yield {"case_id": "warmup", "repeat_index": 0, "discarded": True}
        image_url = _vision_data_url() if vision else None
        for case in cases_for(vision=vision):
            for repeat_index in range(repeat_count):
                image = image_url if case["kind"] == "vision" else None
                speed = _ask(endpoint, model, case["prompt"], image=image)
                stored = {
                    "case_id": case["id"],
                    "kind": case["kind"],
                    "repeat_index": repeat_index,
                    "ttft_ms": speed.ttft_ms,
                    "prompt_tokens": speed.prompt_tokens,
                    "output_tokens": speed.output_tokens,
                    "tokens_per_second": None if speed.error else speed.tokens_per_second,
                    "total_ms": speed.total_ms,
                    "output_preview": preview(speed.text) if speed.text else None,
                    "error": speed.error,
                }
                with connect(db_path) as conn:
                    add_benchmark_result(conn, run_id=run_id, row=stored)
                yield {
                    "case_id": case["id"],
                    "repeat_index": repeat_index,
                    "ttft_ms": stored["ttft_ms"],
                    "tokens_per_second": stored["tokens_per_second"],
                    "error": stored["error"],
                }
    except Exception as exc:
        status = "error"
        yield {"error": str(exc)}
    finally:
        with connect(db_path) as conn:
            finish_benchmark_run(conn, run_id, status)
    yield {"run_id": run_id, "status": status}


def _ask(endpoint: dict, model: str, prompt: str, image: str | None):
    return stream_chat(
        base_url=endpoint["base_url"],
        api_key=endpoint.get("api_key"),
        model=model,
        messages=build_messages(prompt, image),
    )


def _vision_data_url() -> str:
    raw = IMAGE_PATH.read_bytes()
    encoded = base64.standard_b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{encoded}"
