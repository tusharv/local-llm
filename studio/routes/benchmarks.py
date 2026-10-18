import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from studio.benchmarks.runner import BenchmarkBusy, iter_run, start_run_row
from studio.benchmarks.suite import SUITE_VERSION
from studio.db import connect, get_benchmark_run, get_endpoint, get_model_flag, list_benchmark_runs
from studio.engines.ollama import effective_vision
from studio.routes import error

router = APIRouter()


class BenchmarkIn(BaseModel):
    endpoint_id: int
    model: str
    warmup: bool = True
    repeat_count: int = 1


@router.get("/api/benchmarks")
def get_benchmarks(request: Request):
    with connect(request.app.state.db_path) as conn:
        runs = list_benchmark_runs(conn)
    return {"runs": runs, "suite_version": SUITE_VERSION}


@router.get("/api/benchmarks/{run_id}/export")
def export_benchmark(run_id: int, request: Request):
    payload = _run_payload(request, run_id)
    if isinstance(payload, JSONResponse):
        return payload
    return JSONResponse(
        payload,
        headers={"Content-Disposition": f'attachment; filename="benchmark-{run_id}.json"'},
    )


@router.get("/api/benchmarks/{run_id}")
def get_benchmark(run_id: int, request: Request):
    return _run_payload(request, run_id)


@router.post("/api/benchmarks")
def post_benchmark(body: BenchmarkIn, request: Request):
    model = body.model.strip()
    if not model:
        return error("A model is required.", 400)
    if body.repeat_count not in {1, 3}:
        return error("repeat_count must be 1 or 3.", 400)
    with connect(request.app.state.db_path) as conn:
        endpoint = get_endpoint(conn, body.endpoint_id)
        if endpoint is None:
            return error("Endpoint not found.", 404)
        flag = get_model_flag(conn, endpoint["id"], model)
    try:
        run = start_run_row(
            request.app.state.db_path,
            endpoint,
            model,
            body.warmup,
            body.repeat_count,
        )
    except BenchmarkBusy as exc:
        return error(str(exc), 409)
    vision, _source = effective_vision(endpoint, model, flag)

    def generate():
        for event in iter_run(
            db_path=request.app.state.db_path,
            endpoint=endpoint,
            model=model,
            vision=vision,
            warmup=body.warmup,
            repeat_count=body.repeat_count,
            run_id=run["id"],
        ):
            yield "data: " + json.dumps(event) + "\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _run_payload(request: Request, run_id: int):
    with connect(request.app.state.db_path) as conn:
        run = get_benchmark_run(conn, run_id)
    if run is None:
        return error("Benchmark run not found.", 404)
    return {"run": {key: value for key, value in run.items() if key != "results"}, "results": run["results"]}
