from __future__ import annotations

import asyncio
import os
from pathlib import Path

try:  # pragma: no cover - import-time optional dependency
    from playwright.sync_api import Error as PlaywrightError, sync_playwright  # type: ignore
except Exception:  # pragma: no cover
    PlaywrightError = Exception  # type: ignore
    sync_playwright = None

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "MicroMessenger/8.0.40(0x1800282e) NetType/WIFI Language/zh_CN"
)


class BrowserRenderingError(Exception):
    """Raised when Playwright fails to render a page."""


class BrowserRenderer:
    def __init__(self, headless: bool | None = True, timeout_seconds: float = 45.0) -> None:
        self.headless = headless
        # Playwright expects milliseconds for most timeouts.
        self.timeout_ms = int(timeout_seconds * 1000)

    async def render(
        self,
        url: str,
        storage_state: Path | None = None,
        cookies: list[dict[str, str]] | None = None,
    ) -> str:
        if sync_playwright is None:
            raise BrowserRenderingError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._render_sync, url, storage_state, cookies)

    def _render_sync(
        self,
        url: str,
        storage_state: Path | None = None,
        cookies: list[dict[str, str]] | None = None,
    ) -> str:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self._resolve_headless())
                context = browser.new_context(
                    user_agent=MOBILE_UA,
                    viewport={"width": 414, "height": 896},
                    extra_http_headers={
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                        "Referer": "https://mp.weixin.qq.com/",
                    },
                    storage_state=str(storage_state) if storage_state else None,
                )
                if cookies:
                    context.add_cookies(cookies)
                page = context.new_page()
                page.set_default_navigation_timeout(self.timeout_ms)
                page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
                for _ in range(6):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(200)
                page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
                html = page.content()
                context.close()
                browser.close()
                return html
        except PlaywrightError as exc:  # pragma: no cover - requires browser runtime
            raise BrowserRenderingError(str(exc)) from exc

    def _resolve_headless(self) -> bool:
        if self.headless is not None:
            return self.headless
        env_value = os.getenv("PLAYWRIGHT_HEADLESS", "1").strip().lower()
        return env_value not in {"0", "false", "no"}
