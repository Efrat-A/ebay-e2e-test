"""Handlers for eBay overlays that can appear at any moment and block actions.

Registered once per page with Playwright's `page.add_locator_handler`: whenever
one of these overlays is visible and an action (click, fill, ...) is about to
run, Playwright first calls the handler, then retries the action. This covers
dialogs that load late, which a one-off "close popups after navigation" misses.
"""
from __future__ import annotations

import logging
import re

import allure
from playwright.sync_api import Locator, Page

log = logging.getLogger(__name__)


def install_overlay_handlers(page: Page) -> None:
    # "Are you shipping to <zip>?" - confirm, so results only show items that ship to us
    ship_to = page.get_by_role("dialog").filter(
        has_text=re.compile(r"(are you )?shipping to", re.I)
    )

    def confirm_ship_to(dialog: Locator) -> None:
        confirm = dialog.get_by_role("button", name=re.compile(r"^\s*confirm\s*$", re.I))
        if confirm.count():
            log.info("Overlay: confirming ship-to location")
            with allure.step("Overlay: confirm ship-to location"):
                confirm.first.click()
            return
        close = dialog.get_by_role("button", name=re.compile("close|submit|done|^ok$|not now", re.I))
        if close.count():
            log.info("Overlay: closing ship-to dialog")
            close.first.click()
        else:
            # unrecognised button wording - Escape can't hang the handler like a missed selector can
            log.info("Overlay: dismissing ship-to dialog (Escape - no recognised button)")
            page.keyboard.press("Escape")

    page.add_locator_handler(ship_to, confirm_ship_to)

    # Cookie / GDPR consent banner
    consent = page.locator("#gdpr-banner")

    def accept_consent(banner: Locator) -> None:
        log.info("Overlay: accepting cookie banner")
        banner.locator("#gdpr-banner-accept").click()

    page.add_locator_handler(consent, accept_consent)
