from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, HttpUrl


class SnapshotRequest(BaseModel):
    urls: List[HttpUrl]
    force_browser: bool = False


class SnapshotResponseItem(BaseModel):
    original_url: HttpUrl
    archived_url: Optional[str] = None
    archived_relative_url: Optional[str] = None
    status: Literal["success", "failed"]
    error: Optional[str] = None


class SnapshotResponse(BaseModel):
    results: List[SnapshotResponseItem]


class HistoryRecord(BaseModel):
    id: str
    original_url: HttpUrl
    archived_url: Optional[str] = None
    archived_relative_url: Optional[str] = None
    status: Literal["success", "failed"]
    error: Optional[str] = None
    captured_at: str


class HistoryResponse(BaseModel):
    items: List[HistoryRecord]
