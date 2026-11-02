from __future__ import annotations

import logging

import allure

from pages.base_page import BasePage
from utils.price_parser import Price, parse_price

log = logging.getLogger(__name__)


class CartPage(BasePage):
    SUBTOTAL = [
        "[data-test-id='SUBTOTAL']",
        "div.val-col.total-row span",
        "xpath=//*[contains(translate(text(),'SUBTOAL','subtoal'),'subtotal')]/following::*[contains(text(),'$') or contains(text(),'₪') or contains(text(),'ILS')][1]",
    ]

    def open_cart(self) -> None:
        with allure.step("Open cart"):
            self.open(self.config["cart_url"])

    def read_subtotal(self) -> Price:
        text = self.smart("cart_subtotal", self.SUBTOTAL).resolve(timeout_ms=10000).inner_text()
        price = parse_price(text, range_strategy="max")
        if price is None:
            raise AssertionError(f"Could not parse cart subtotal from '{text}'")
        log.info("Cart subtotal: %s %s", price.amount, price.currency or "")
        allure.attach(text, name="cart_subtotal_raw", attachment_type=allure.attachment_type.TEXT)
        return price
