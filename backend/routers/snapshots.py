from __future__ import annotations

import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends

from backend.core.config import settings
from backend.dependencies import get_history_repository, get_snapshot_service
from backend.models.schemas import (
    HistoryRecord,
    HistoryResponse,
    SnapshotRequest,
    SnapshotResponse,
    SnapshotResponseItem,
)
from backend.services.history_repository import HistoryEntry, HistoryRepository
from backend.services.snapshot_service import SnapshotError, SnapshotService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["snapshots"])


@router.post("/snapshots", response_model=SnapshotResponse)
async def create_snapshots(
    payload: SnapshotRequest,
    service: SnapshotService = Depends(get_snapshot_service),
    history_repo: HistoryRepository = Depends(get_history_repository),
) -> SnapshotResponse:
    results: List[SnapshotResponseItem] = []
    history_entries: List[HistoryEntry] = []

    for url in payload.urls:
        logger.info("Processing snapshot request", extra={"url": str(url)})
        try:
            metadata = await service.create_snapshot(str(url), force_browser=payload.force_browser)
            logger.info(
                "Snapshot created",
                extra={"url": str(url), "file": str(metadata.archived_path)},
            )
            results.append(
                SnapshotResponseItem(
                    original_url=url,
                    archived_url=metadata.archived_url,
                    archived_relative_url=metadata.relative_url,
                    status="success",
                    error=None,
                )
            )
            history_entries.append(
                HistoryEntry(
                    id=uuid.uuid4().hex,
                    original_url=str(url),
                    archived_url=metadata.archived_url,
                    archived_relative_url=metadata.relative_url,
                    status="success",
                    error=None,
                    captured_at=metadata.captured_at.isoformat(),
                )
            )
        except SnapshotError as exc:
            logger.warning(
                "Snapshot failed",
                extra={"url": str(url), "error": str(exc)},
            )
            results.append(
                SnapshotResponseItem(
                    original_url=url,
                    archived_url=None,
                    archived_relative_url=None,
                    status="failed",
                    error=str(exc),
                )
            )
            history_entries.append(
                HistoryEntry(
                    id=uuid.uuid4().hex,
                    original_url=str(url),
                    archived_url=None,
                    archived_relative_url=None,
                    status="failed",
                    error=str(exc),
                    captured_at=settings.current_timestamp(),
                )
            )

    if history_entries:
        await history_repo.append(history_entries)
    return SnapshotResponse(results=results)


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    limit: int = 50,
    history_repo: HistoryRepository = Depends(get_history_repository),
) -> HistoryResponse:
    limit = max(1, min(limit, 200))
    records = await history_repo.list_recent(limit)
    items = [
        HistoryRecord(
            id=entry.id,
            original_url=entry.original_url,
            archived_url=entry.archived_url,
            archived_relative_url=entry.archived_relative_url,
            status=entry.status,
            error=entry.error,
            captured_at=entry.captured_at,
        )
        for entry in records
    ]
    return HistoryResponse(items=items)
