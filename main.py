import os
import signal
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, select, text

import models  # noqa: F401
from api.router import api_router
from core.config import get_settings
from core.db import AsyncSessionLocal, Base, engine
from core.dynamic_cors import DynamicCORSMiddleware
from core.rate_limit import RateLimitMiddleware
from models.project import Project
from utils.origin import normalize_allowed_origin

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


def _ensure_project_allowed_origin_column(connection) -> None:
    inspector = inspect(connection)
    columns = {column["name"] for column in inspector.get_columns("projects")}
    if "allowed_origin" in columns:
        return

    connection.execute(text("ALTER TABLE projects ADD COLUMN allowed_origin VARCHAR(255)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_allowed_origin ON projects (allowed_origin)"))


async def _backfill_project_allowed_origins() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).where(Project.allowed_origin.is_(None)))
        projects = result.scalars().all()
        updated = False

        for project in projects:
            normalized_origin = normalize_allowed_origin(project.name)
            if normalized_origin is None:
                continue
            project.allowed_origin = normalized_origin
            updated = True

        if updated:
            await session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup lifecycle ensures DB schema exists for local/dev container runs.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_ensure_project_allowed_origin_column)
    await _backfill_project_allowed_origins()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Multi-tenant AI Gateway with RAG",
    lifespan=lifespan,
)

app.add_middleware(
    DynamicCORSMiddleware,
    static_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RateLimitMiddleware, redis_url=settings.redis_url)
app.include_router(api_router)
app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")


@app.get("/")
async def landing_page() -> FileResponse:
    return FileResponse(WEB_DIR / "landing.html")


@app.get("/admin")
async def admin_page() -> FileResponse:
    return FileResponse(WEB_DIR / "admin.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


def _resolve_dramatiq_command() -> list[str]:
    scripts_dir = Path(sys.executable).resolve().parent
    dramatiq_binary = scripts_dir / "dramatiq"
    if dramatiq_binary.exists():
        return [str(dramatiq_binary), "workers.worker_entrypoint"]
    return [sys.executable, "-m", "dramatiq", "workers.worker_entrypoint"]


def _stop_worker_process(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return

    # Graceful first: let Dramatiq stop its own worker subprocesses.
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _start_worker_process() -> subprocess.Popen[str]:
    command = _resolve_dramatiq_command()
    return subprocess.Popen(command, cwd=BASE_DIR, env=os.environ.copy())

if __name__ == "__main__":
    import uvicorn

    worker_process = _start_worker_process()

    try:
        uvicorn.run(app, host=settings.app_host, port=settings.app_port)
    finally:
        _stop_worker_process(worker_process)