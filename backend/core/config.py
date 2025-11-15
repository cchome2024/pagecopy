from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    snapshot_root: Path = Path("./data/snapshots")
    snapshot_base_url: str = "http://localhost:8000/snapshots"
    history_file: Path = Path("./data/history.jsonl")
    request_timeout: float = 20.0
    browser_timeout: float = 45.0
    playwright_headless: bool = True
    playwright_session_dir: Path | None = Path("./data/sessions")
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )
    js_heavy_hosts: List[str] = Field(default_factory=lambda: ["mp.weixin.qq.com"])

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @staticmethod
    def current_timestamp() -> str:
        return datetime.now(tz=timezone.utc).isoformat()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
