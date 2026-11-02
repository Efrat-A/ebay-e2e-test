from __future__ import annotations

import logging
import random

import allure
from playwright.sync_api import Locator

from pages.base_page import BasePage
from utils.retry import retry

log = logging.getLogger(__name__)


class ItemPage(BasePage):
    ADD_TO_CART = [
        "#atcBtn_btn_1",
        "a[data-testid='ux-call-to-action']:has-text('Add to cart')",
        "button:has-text('Add to cart')",
    ]
    # Old layout: native <select>; new layout: listbox buttons
    SELECT_VARIANTS = "select.x-msku__select-box, select[id^='x-msku__select-box']"
    LISTBOX_VARIANTS = "div.x-msku-evo button.listbox-button__control, button[aria-haspopup='listbox']"
    ADDED_CONFIRMATION = [
        "div[role='dialog']:has-text('Added to cart')",
        "text=/added to (your )?cart/i",
        "h1:has-text('Shopping cart')",
    ]

    @retry(attempts=2, delay_sec=1.5)
    def add_to_cart(self, url: str, index: int) -> None:
        with allure.step(f"Add item {index}: {url}"):
            self.open(url)
            self._select_random_variants()
            self.smart("add_to_cart", self.ADD_TO_CART).resolve().click()
            self.smart("added_confirmation", self.ADDED_CONFIRMATION).resolve(timeout_ms=10000)
            self.screenshot(f"item_{index}_added")
            log.info("Item %d added: %s", index, url)

    def _select_random_variants(self) -> None:
        for select in self.page.locator(self.SELECT_VARIANTS).all():
            options = [o for o in select.locator("option").all()
                       if o.get_attribute("value") not in (None, "", "-1") and o.is_enabled()]
            if options:
                choice = random.choice(options).get_attribute("value")
                select.select_option(choice)
                log.info("Variant (select) -> %s", choice)
        for button in self.page.locator(self.LISTBOX_VARIANTS).all():
            self._pick_from_listbox(button)

    def _pick_from_listbox(self, button: Locator) -> None:
        button.click()
        options = self.page.locator(
            "div.listbox__options[role='listbox'] div[role='option']:not([aria-disabled='true'])"
        ).filter(has_not_text="Select")
        count = options.count()
        if count:
            choice = options.nth(random.randrange(count))
            log.info("Variant (listbox) -> %s", choice.inner_text().strip())
            choice.click()
        else:
            self.page.keyboard.press("Escape")
