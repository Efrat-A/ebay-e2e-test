from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Sequence

import allure
from playwright.sync_api import Page

from utils.smart_locator import SmartLocator

log = logging.getLogger(__name__)
SCREENSHOTS = Path(__file__).resolve().parent.parent / "reports" / "screenshots"


class BasePage:
    """Shared behaviour for every page object: navigation, popups, screenshots."""

    # Overlays eBay shows on and off (cookie banner, sign-in nudges, etc.)
    _DISMISSABLES = [
        "#gdpr-banner-accept",
        "button[aria-label='Close dialog']",
        "button.lightbox-dialog__close",
        "button[aria-label='Close']",
    ]

    def __init__(self, page: Page, config: dict[str, Any]):
        self.page = page
        self.config = config
        self.page.set_default_timeout(config["timeouts"]["default_ms"])
        self.page.set_default_navigation_timeout(config["timeouts"]["navigation_ms"])

    def smart(self, name: str, candidates: Sequence[str]) -> SmartLocator:
        return SmartLocator(self.page, name, candidates)

    def open(self, url: str) -> None:
        log.info("Open %s", url)
        self.page.goto(url, wait_until="domcontentloaded")
        self.dismiss_popups()

    def dismiss_popups(self) -> None:
        for selector in self._DISMISSABLES:
            btn = self.page.locator(selector).first
            try:
                if btn.is_visible(timeout=300):
                    btn.click()
            except Exception:  # popups are best-effort, never fail the test on them
                pass

    def screenshot(self, name: str, full_page: bool = False) -> Path:
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w\-]+", "_", name)
        path = SCREENSHOTS / f"{safe}.png"
        self.page.screenshot(path=str(path), full_page=full_page)
        allure.attach.file(str(path), name=name, attachment_type=allure.attachment_type.PNG)
        return path
