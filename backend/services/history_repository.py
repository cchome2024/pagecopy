from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(slots=True)
class HistoryEntry:
    id: str
    original_url: str
    archived_url: str | None
    archived_relative_url: str | None
    status: str
    error: str | None
    captured_at: str


class HistoryRepository:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def append(self, entries: Iterable[HistoryEntry]) -> None:
        payload = "".join(json.dumps(asdict(entry), ensure_ascii=False) + "\n" for entry in entries)
        if not payload:
            return
        async with self._lock:
            await asyncio.to_thread(self._write, payload)

    async def list_recent(self, limit: int = 100) -> List[HistoryEntry]:
        if not self.file_path.exists():
            return []
        async with self._lock:
            return await asyncio.to_thread(self._read_last, limit)

    def _write(self, chunk: str) -> None:
        with self.file_path.open("a", encoding="utf-8") as handler:
            handler.write(chunk)

    def _read_last(self, limit: int) -> List[HistoryEntry]:
        with self.file_path.open("r", encoding="utf-8") as handler:
            lines = handler.readlines()
        records = [json.loads(line) for line in lines[-limit:] if line.strip()]
        entries = [
            HistoryEntry(
                id=item.get("id") or str(uuid.uuid4()),
                original_url=item["original_url"],
                archived_url=item.get("archived_url"),
                archived_relative_url=item.get("archived_relative_url"),
                status=item.get("status", "failed"),
                error=item.get("error"),
                captured_at=item.get("captured_at", ""),
            )
            for item in records
        ]
        entries.reverse()
        return entries
