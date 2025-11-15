from __future__ import annotations

from functools import lru_cache

from backend.core.config import settings
from backend.services.browser_renderer import BrowserRenderer
from backend.services.history_repository import HistoryRepository
from backend.services.snapshot_service import SnapshotService


@lru_cache
def _browser_renderer() -> BrowserRenderer:
    return BrowserRenderer(
        headless=settings.playwright_headless,
        timeout_seconds=settings.browser_timeout,
    )


@lru_cache
def get_snapshot_service() -> SnapshotService:
    return SnapshotService(
        snapshot_root=settings.snapshot_root,
        snapshot_base_url=settings.snapshot_base_url,
        request_timeout=settings.request_timeout,
        browser_renderer=_browser_renderer(),
        js_heavy_hosts=settings.js_heavy_hosts,
    )


@lru_cache
def get_history_repository() -> HistoryRepository:
    return HistoryRepository(settings.history_file)
