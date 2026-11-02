from __future__ import annotations

import logging

import allure

from pages.base_page import BasePage
from utils.errors import PriceParseError
from utils.price_parser import Price, parse_price

log = logging.getLogger(__name__)


class CartPage(BasePage):
    SUBTOTAL = [
        "[data-test-id='SUBTOTAL']",
        "div.val-col.total-row span",
        "xpath=//*[contains(translate(text(),'SUBTOAL','subtoal'),'subtotal')]"
        "/following::*[contains(text(),'$') or contains(text(),'₪') or contains(text(),'ILS')][1]",
    ]

    @allure.step("Open shopping cart")
    def open_cart(self) -> None:
        self.open(self.config["cart_url"])

    @allure.step("Read cart subtotal")
    def read_subtotal(self) -> Price:
        text = self.smart("cart subtotal", self.SUBTOTAL).resolve(timeout_ms=10000).inner_text()
        allure.attach(text, name="cart_subtotal_raw", attachment_type=allure.attachment_type.TEXT)
        price = parse_price(text, range_strategy="max")
        if price is None:
            raise PriceParseError(text, "cart subtotal")
        log.info("Cart subtotal: %s %s", price.amount, price.currency or "")
        return price
