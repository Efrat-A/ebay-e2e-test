from __future__ import annotations

import logging
import random

import allure
from playwright.sync_api import Locator

from pages.base_page import BasePage
from utils.errors import AddToCartError, BotChallengeError, ElementNotFoundError
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

    @allure.step("Add item #{index} to cart")
    def add_to_cart(self, url: str, index: int) -> None:
        try:
            self._add_to_cart_with_retry(url, index)
        except BotChallengeError:
            raise
        except ElementNotFoundError as exc:
            raise AddToCartError(index, url, str(exc)) from exc

    @retry(attempts=2, delay_sec=1.5, exceptions=(ElementNotFoundError,))
    def _add_to_cart_with_retry(self, url: str, index: int) -> None:
        self.open(url)
        self.select_random_variants()
        self.click_add_to_cart()
        self.smart("'added to cart' confirmation", self.ADDED_CONFIRMATION).resolve(timeout_ms=10000)
        self.screenshot(f"item_{index}_added")
        log.info("Item %d added: %s", index, url)

    @allure.step("Select random variants (size / color / quantity)")
    def select_random_variants(self) -> None:
        chosen = []
        for select in self.page.locator(self.SELECT_VARIANTS).all():
            options = [o for o in select.locator("option").all()
                       if o.get_attribute("value") not in (None, "", "-1") and o.is_enabled()]
            if options:
                option = random.choice(options)
                select.select_option(option.get_attribute("value"))
                chosen.append(option.inner_text().strip())
        for button in self.page.locator(self.LISTBOX_VARIANTS).all():
            picked = self._pick_from_listbox(button)
            if picked:
                chosen.append(picked)
        allure.dynamic.parameter("variants", ", ".join(chosen) or "none required")

    @allure.step("Click 'Add to cart'")
    def click_add_to_cart(self) -> None:
        self.smart("Add to cart button", self.ADD_TO_CART).resolve().click()

    def _pick_from_listbox(self, button: Locator) -> str | None:
        button.click()
        options = self.page.locator(
            "div.listbox__options[role='listbox'] div[role='option']:not([aria-disabled='true'])"
        ).filter(has_not_text="Select")
        count = options.count()
        if not count:
            self.page.keyboard.press("Escape")
            return None
        choice = options.nth(random.randrange(count))
        text = choice.inner_text().strip()
        choice.click()
        return text
