from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Open a headful Playwright browser so you can log into a site manually. "
            "Press Enter once the login finishes and the current session will be saved."
        )
    )
    parser.add_argument("url", help="The page URL that requires login (e.g. https://mp.weixin.qq.com/).")
    parser.add_argument(
        "--output",
        type=Path,
        help="Where to store the storage_state JSON. Defaults to data/sessions/<host>.json.",
    )
    parser.add_argument(
        "--browser",
        default="chromium",
        choices=["chromium", "firefox", "webkit"],
        help="Playwright browser to launch (default: chromium).",
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1280,
        help="Viewport width when logging in (default: 1280).",
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=720,
        help="Viewport height when logging in (default: 720).",
    )
    return parser.parse_args()


def resolve_output_path(raw_url: str, explicit: Path | None) -> Path:
    if explicit:
        explicit.parent.mkdir(parents=True, exist_ok=True)
        return explicit
    hostname = urlparse(raw_url).hostname or "session"
    sessions_dir = Path("data") / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir / f"{hostname}.json"


def main() -> int:
    args = parse_args()
    output_path = resolve_output_path(args.url, args.output)
    print(f"[+] Launching Playwright ({args.browser}) in headful mode ...")
    with sync_playwright() as playwright:
        browser_type = getattr(playwright, args.browser)
        browser = browser_type.launch(headless=False)
        context = browser.new_context(
            viewport={"width": args.viewport_width, "height": args.viewport_height},
        )
        page = context.new_page()
        print(f"[+] Opening {args.url}")
        page.goto(args.url, wait_until="load")
        print(
            "\n--- Manual Login Required ---\n"
            "1. Complete all login steps inside the opened browser window.\n"
            "2. Verify that the page shows the authenticated content you expect.\n"
            "3. Return to this terminal and press Enter to save the session.\n"
        )
        input("Press Enter here once login is complete to capture the session...")
        context.storage_state(path=str(output_path))
        print(f"[+] Session saved to {output_path}")
        context.close()
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
