"""Collects what the browser reports while a test runs.

* console messages      -> logging.DEBUG (errors -> WARNING)
* uncaught page errors  -> logging.WARNING
* HTTP responses >= 400 -> logging.DEBUG (403/429 -> WARNING, usually bot protection)

Everything is also kept in memory so it can be attached to the Allure
report when a test fails.
"""
from __future__ import annotations

import logging
from datetime import datetime

from playwright.sync_api import ConsoleMessage, Page, Response

log = logging.getLogger("browser")


class BrowserLogCollector:
    def __init__(self) -> None:
        self.entries: list[str] = []

    def attach_to(self, page: Page) -> "BrowserLogCollector":
        page.on("console", self._on_console)
        page.on("pageerror", self._on_page_error)
        page.on("response", self._on_response)
        return self

    def __bool__(self) -> bool:
        return bool(self.entries)

    def as_text(self) -> str:
        return "\n".join(self.entries)

    def _record(self, level: int, text: str) -> None:
        self.entries.append(f"{datetime.now():%H:%M:%S.%f}"[:-3] + f" {logging.getLevelName(level):7} {text}")
        log.log(level, text)

    def _on_console(self, msg: ConsoleMessage) -> None:
        url = (msg.location or {}).get("url", "")
        level = logging.WARNING if msg.type == "error" else logging.DEBUG
        self._record(level, f"[console.{msg.type}] {msg.text}" + (f"  ({url})" if url else ""))

    def _on_page_error(self, error: Exception) -> None:
        self._record(logging.WARNING, f"[pageerror] {error}")

    def _on_response(self, response: Response) -> None:
        if response.status >= 400:
            level = logging.WARNING if response.status in (403, 429) else logging.DEBUG
            self._record(level, f"[http {response.status}] {response.request.method} {response.url}")
