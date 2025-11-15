from __future__ import annotations

import asyncio
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.config import settings
from backend.routers import snapshots

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    app = FastAPI(
        title="PageCopy Snapshot Service",
        description="Backend API for capturing and serving static HTML snapshots.",
        version="0.1.0",
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    settings.snapshot_root.mkdir(parents=True, exist_ok=True)

    app.include_router(snapshots.router, prefix="/api")
    app.mount(
        "/snapshots",
        StaticFiles(directory=settings.snapshot_root, html=True),
        name="snapshots",
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "timestamp": settings.current_timestamp()}

    return app


app = create_app()
