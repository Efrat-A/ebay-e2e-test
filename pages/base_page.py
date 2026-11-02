from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, Sequence

import allure
from playwright.sync_api import Error as PlaywrightError, Page

from utils.errors import AccessBlockedError, BotChallengeError, NetworkError, PageErrorError
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
    _CHALLENGE_URL = re.compile(r"/splashui/(challenge|captcha)", re.I)
    _CHALLENGE_FRAME = "iframe[src*='captcha'], iframe[title*='challenge' i]"

    def __init__(self, page: Page, config: dict[str, Any]):
        self.page = page
        self.config = config
        self.page.set_default_timeout(config["timeouts"]["default_ms"])
        self.page.set_default_navigation_timeout(config["timeouts"]["navigation_ms"])

    def smart(self, name: str, candidates: Sequence[str]) -> SmartLocator:
        return SmartLocator(self.page, name, candidates)

    _BLOCKED_STATUSES = (403, 429)
    # Titles / headings of eBay (and CDN) error pages that are worth a refresh.
    # The phrase must be the whole text or be followed by punctuation, so an item
    # page titled e.g. "Access Denied Hoodie" is not mistaken for an error page.
    _ERROR_PAGE_TEXT = re.compile(
        r"^\s*(access denied|something went wrong|we'?re sorry|page (is )?not responding"
        r"|service unavailable|temporarily unavailable|bad gateway|gateway time-?out)\s*([.!,:\-–]|$)",
        re.I,
    )
    # Distinctive sentences from eBay's own error page body (e.g. "Please go back and try again").
    # Specific enough to search anywhere in the page text; item descriptions live in an iframe.
    _ERROR_BODY_TEXT = re.compile(
        r"please go back and try again|we'?re having trouble (connecting|loading)|looks like this page doesn'?t exist",
        re.I,
    )

    @allure.step("Open {url}")
    def open(self, url: str) -> None:
        self.navigate(url)
        self.dismiss_popups()

    def navigate(self, url: str) -> None:
        """Go to `url`, wait for the page to load, and make sure it is not an error page.

        Error pages (HTTP 403/429/5xx, an error title/heading, or eBay's "Please go back
        and try again" text) are retried with growing pauses by loading the ORIGINAL url
        again - not reload(), which would just reload an error page eBay redirected to.
        After the configured retries a clear error is raised.
        CAPTCHA pages are never refreshed - they raise BotChallengeError right away.
        """
        retries = self.config.get("retry", {}).get("page_error_retries", 2)
        backoff = self.config.get("retry", {}).get("page_error_backoff_sec", 3)
        log.info("Navigate %s", url)
        response = self._goto(url)

        for attempt in range(1, retries + 2):
            self._wait_for_load()
            self.ensure_no_bot_challenge()
            status = response.status if response else None
            reason = self._error_page_reason(status)
            if reason is None:
                if status and status >= 400:
                    log.warning("HTTP %s for %s (page content looks fine, continuing)", status, url)
                return
            if self.page.url != url:
                reason += f", redirected to {self.page.url}"
            if attempt > retries:
                self.screenshot(f"error_page_{status or 'content'}")
                if status in self._BLOCKED_STATUSES:
                    raise AccessBlockedError(status, url, self.config.get("slow_mo_ms", 0), attempt)
                raise PageErrorError(reason, url, attempt)
            pause = backoff * 2 ** (attempt - 1)
            with allure.step(f"Error page ({reason}) - try again #{attempt} after {pause:g}s"):
                log.warning("Error page (%s) for %s - try again #%d in %gs", reason, url, attempt, pause)
                time.sleep(pause)
                response = self._goto(url)

    _NET_ERROR = re.compile(r"net::ERR_[A-Z_]+|NS_ERROR_[A-Z_]+")

    def _goto(self, url: str):
        try:
            return self.page.goto(url, wait_until="domcontentloaded")
        except PlaywrightError as exc:
            match = self._NET_ERROR.search(str(exc))
            if match:
                raise NetworkError(url, match.group(0)) from exc
            raise

    def _wait_for_load(self) -> None:
        """Best-effort wait for the full page load; eBay keeps loading ads, so don't fail on it."""
        try:
            self.page.wait_for_load_state("load", timeout=self.config["timeouts"]["navigation_ms"] // 2)
        except Exception:
            log.debug("Page 'load' event not reached in time - continuing with DOM content")

    def _error_page_reason(self, status: int | None) -> str | None:
        if status in self._BLOCKED_STATUSES or (status and status >= 500):
            return f"HTTP {status}"
        title = self.page.title() or ""
        heading = self.page.locator("h1").first
        heading_text = heading.inner_text(timeout=1000) if heading.count() else ""
        for text in (title, heading_text):
            if self._ERROR_PAGE_TEXT.match(text):
                return f"'{text.strip()[:60]}'"
        try:
            body = self.page.locator("body").inner_text(timeout=2000)
        except Exception:
            body = ""
        match = self._ERROR_BODY_TEXT.search(body)
        if match:
            return f"page says '{match.group(0)}'"
        return None

    def ensure_no_bot_challenge(self) -> None:
        if self._CHALLENGE_URL.search(self.page.url) or self.page.locator(self._CHALLENGE_FRAME).count():
            self.screenshot("bot_challenge")
            raise BotChallengeError(self.page.url)

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
