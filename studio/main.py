from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from studio.db import init_db
from studio.routes import benchmarks, chat, endpoints, health, models


def create_app(data_dir: Path | None = None) -> FastAPI:
    root = Path(data_dir) if data_dir is not None else Path("data")
    uploads = root / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    uploads.mkdir(parents=True, exist_ok=True)
    db_path = root / "studio.db"
    init_db(db_path)

    app = FastAPI(title="Local LLM Studio")
    app.state.data_dir = root
    app.state.uploads_dir = uploads
    app.state.db_path = db_path
    app.include_router(health.router)
    app.include_router(endpoints.router)
    app.include_router(models.router)
    app.include_router(chat.router)
    app.include_router(benchmarks.router)

    @app.get("/uploads/{filename}")
    def serve_upload(filename: str):
        if filename != Path(filename).name or filename in {".", ".."}:
            return JSONResponse({"error": "Not found."}, status_code=404)
        path = (uploads / filename).resolve()
        if path.parent != uploads.resolve() or not path.is_file():
            return JSONResponse({"error": "Not found."}, status_code=404)
        return FileResponse(path)

    dist = _dist_dir()
    if dist is not None:
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


def _dist_dir() -> Path | None:
    candidates = [
        Path("web/dist"),
        Path(__file__).resolve().parents[1] / "web" / "dist",
    ]
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None
