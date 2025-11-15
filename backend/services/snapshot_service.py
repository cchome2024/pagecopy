from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import aiofiles  # type: ignore[import-not-found]
import httpx

from backend.services.browser_renderer import (
    BrowserRenderer,
    BrowserRenderingError,
)


class SnapshotError(Exception):
    """Base exception for snapshot failures."""


class SnapshotUnsupportedError(SnapshotError):
    """Raised when the resource cannot be archived."""


@dataclass(slots=True)
class SnapshotMetadata:
    original_url: str
    archived_path: Path
    archived_url: str
    relative_url: str
    captured_at: datetime


class SnapshotService:
    def __init__(
        self,
        snapshot_root: Path,
        snapshot_base_url: str,
        request_timeout: float,
        browser_renderer: Optional[BrowserRenderer] = None,
        js_heavy_hosts: Optional[list[str]] = None,
    ) -> None:
        self.snapshot_root = snapshot_root
        self.snapshot_root.mkdir(parents=True, exist_ok=True)
        self.snapshot_base_url = snapshot_base_url.rstrip("/")
        self.request_timeout = request_timeout
        self.browser_renderer = browser_renderer
        self.js_heavy_hosts = {host.lower() for host in (js_heavy_hosts or [])}

    async def create_snapshot(self, url: str, force_browser: bool = False) -> SnapshotMetadata:
        captured_at = datetime.now(timezone.utc)
        html: Optional[str] = None
        use_browser = force_browser or self._should_use_browser(url)
        http_error: Optional[SnapshotError] = None

        if not use_browser:
            try:
                html = await self._fetch_via_http(url, captured_at)
            except SnapshotError as exc:
                http_error = exc

        if html is None:
            if self.browser_renderer is None:
                raise http_error or SnapshotError("Browser renderer is not configured.")
            html = await self._render_with_browser(url, captured_at)

        filename = self._build_filename(url, captured_at)
        archived_path = self.snapshot_root / filename
        await self._write_file(archived_path, html)
        relative_url = f"/snapshots/{filename}"
        archived_url = f"{self.snapshot_base_url}/{filename}"

        return SnapshotMetadata(
            original_url=url,
            archived_path=archived_path,
            archived_url=archived_url,
            relative_url=relative_url,
            captured_at=captured_at,
        )

    async def _fetch_via_http(self, url: str, captured_at: datetime) -> str:
        try:
            async with httpx.AsyncClient(
                timeout=self.request_timeout, follow_redirects=True
            ) as client:
                response = await client.get(url)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise SnapshotError("HTTP fetch timed out.") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response else "unknown"
            raise SnapshotError(f"HTTP fetch failed with status {status}.") from exc
        except httpx.RequestError as exc:
            raise SnapshotError(f"HTTP fetch error: {exc}") from exc
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise SnapshotUnsupportedError("Unsupported content type for snapshot.")

        comment = self._build_comment(url, captured_at)
        content = self._sanitize_html(response.text, url)
        return f"{comment}\n{content}"

    async def _render_with_browser(self, url: str, captured_at: datetime) -> str:
        if not self.browser_renderer:
            raise SnapshotError("Browser renderer is not configured.")
        try:
            rendered_html = await self.browser_renderer.render(url)
        except BrowserRenderingError as exc:
            raise SnapshotError(str(exc)) from exc
        comment = self._build_comment(url, captured_at)
        content = self._sanitize_html(rendered_html, url)
        return f"{comment}\n{content}"

    async def _write_file(self, path: Path, html: str) -> None:
        async with aiofiles.open(path, "w", encoding="utf-8") as file:
            await file.write(html)

    def _build_filename(self, url: str, captured_at: datetime) -> str:
        digest = hashlib.sha256(f"{url}{captured_at.timestamp()}".encode("utf-8")).hexdigest()[:10]
        return f"{captured_at.strftime('%Y%m%d%H%M%S')}_{digest}.html"

    def _should_use_browser(self, url: str) -> bool:
        hostname = urlparse(url).hostname or ""
        return hostname.lower() in self.js_heavy_hosts

    @staticmethod
    def _build_comment(url: str, captured_at: datetime) -> str:
        return (
            "<!--\n"
            f"Archived from: {url}\n"
            f"Captured at (UTC): {captured_at.isoformat()}\n"
            "Generated by PageCopy Snapshot Service\n"
            "-->"
        )

    def _sanitize_html(self, html: str, url: str) -> str:
        html_with_base = self._inject_base_tag(html, url)
        return self._strip_scripts(html_with_base)

    @staticmethod
    def _inject_base_tag(html: str, url: str) -> str:
        """Insert a <base> tag so relative assets resolve to the original origin."""
        base_tag = f'<base href="{url}" />'
        pattern = re.compile(r"(<head[^>]*>)", re.IGNORECASE)
        if pattern.search(html):
            return pattern.sub(rf"\1\n    {base_tag}", html, count=1)
        return f"<head>{base_tag}</head>\n{html}"

    @staticmethod
    def _strip_scripts(html: str) -> str:
        script_re = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
        return script_re.sub("", html)
