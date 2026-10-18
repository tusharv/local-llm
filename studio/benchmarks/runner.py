import base64
import threading
from collections.abc import Iterator
from pathlib import Path

from studio.assets import IMAGE_PATH
from studio.benchmarks.suite import SUITE_VERSION, cases_for
from studio.db import add_benchmark_result, connect, create_benchmark_run, finish_benchmark_run, has_running_benchmark
from studio.engines.images import generate_image
from studio.engines.openai_compatible import build_messages, preview, stream_chat

_run_lock = threading.Lock()


class BenchmarkBusy(RuntimeError):
    """Another benchmark is still running."""


def start_run_row(db_path, endpoint: dict, model: str, warmup: bool, repeat_count: int, profile: str = "standard") -> dict:
    with _run_lock:
        with connect(db_path) as conn:
            if has_running_benchmark(conn):
                raise BenchmarkBusy("A benchmark is already running.")
            return create_benchmark_run(conn, endpoint_id=endpoint["id"], endpoint_kind=endpoint["kind"],
                                        model=model, suite_version=SUITE_VERSION, warmup=warmup,
                                        repeat_count=repeat_count, profile=profile)


def iter_run(*, db_path, endpoint: dict, model: str, vision: bool, warmup: bool,
             repeat_count: int, run_id: int, profile: str = "standard") -> Iterator[dict]:
    status = "done"
    cases = cases_for(vision=vision, profile=profile)
    total = len(cases) * repeat_count
    completed = 0
    uploads_dir = Path(db_path).parent / "uploads"
    with connect(db_path) as conn:
        conn.execute("UPDATE benchmark_run SET expected_results = ? WHERE id = ?", (total, run_id))
    try:
        yield {"event": "plan", "run_id": run_id, "total": total, "cases": [{"id": c["id"], "title": c["title"], "kind": c["kind"]} for c in cases]}
        if warmup:
            yield {"event": "warmup", "total": total, "completed": 0}
            if profile == "image":
                result = generate_image(endpoint, model, cases[0]["prompt"], uploads_dir)
                if result.get("image_path"):
                    (uploads_dir / result["image_path"]).unlink(missing_ok=True)
                warmup_error = result.get("error")
            else:
                warmup_error = _ask(endpoint, model, "Reply with one word: hello.", image=None).error
            if warmup_error:
                raise RuntimeError(f"Warmup failed: {warmup_error}")
            yield {"event": "warmup_complete", "case_id": "warmup", "repeat_index": 0, "discarded": True}
        image_url = _vision_data_url() if vision and profile == "standard" else None
        for case in cases:
            for repeat_index in range(repeat_count):
                yield {"event": "case_started", "case_id": case["id"], "title": case["title"], "repeat_index": repeat_index, "completed": completed, "total": total}
                stored = {"case_id": case["id"], "kind": case["kind"], "repeat_index": repeat_index}
                try:
                    if case["kind"] == "image":
                        stored.update(generate_image(endpoint, model, case["prompt"], uploads_dir))
                    else:
                        speed = _ask(endpoint, model, case["prompt"], image=image_url if case["kind"] == "vision" else None)
                        stored.update({"ttft_ms": speed.ttft_ms, "prompt_tokens": speed.prompt_tokens,
                                       "output_tokens": speed.output_tokens, "tokens_per_second": None if speed.error else speed.tokens_per_second,
                                       "total_ms": speed.total_ms, "output_preview": preview(speed.text) if speed.text else None,
                                       "output_text": speed.text[:32000], "token_basis": speed.token_basis, "error": speed.error})
                except Exception as exc:
                    stored["error"] = str(exc)
                if stored.get("error"):
                    status = "error"
                with connect(db_path) as conn:
                    add_benchmark_result(conn, run_id=run_id, row=stored)
                completed += 1
                yield {"event": "case_complete", "case_id": case["id"], "repeat_index": repeat_index,
                       "completed": completed, "total": total, "ttft_ms": stored.get("ttft_ms"),
                       "tokens_per_second": stored.get("tokens_per_second"), "error": stored.get("error")}
    except Exception as exc:
        status = "error"
        with connect(db_path) as conn:
            conn.execute("UPDATE benchmark_run SET error = ? WHERE id = ?", (str(exc), run_id))
        yield {"event": "error", "error": str(exc)}
    finally:
        if completed < total:
            status = "error"
        with connect(db_path) as conn:
            finish_benchmark_run(conn, run_id, status)
    yield {"event": "finished", "run_id": run_id, "status": status, "completed": completed, "total": total}


def _ask(endpoint: dict, model: str, prompt: str, image: str | None):
    return stream_chat(base_url=endpoint["base_url"], api_key=endpoint.get("api_key"), model=model,
                       messages=build_messages(prompt, image))


def _vision_data_url() -> str:
    encoded = base64.standard_b64encode(IMAGE_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
