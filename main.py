import os
import signal
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import models  # noqa: F401
from api.router import api_router
from core.config import get_settings
from core.db import Base, engine
from core.rate_limit import RateLimitMiddleware

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup lifecycle ensures DB schema exists for local/dev container runs.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Multi-tenant AI Gateway with RAG",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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