"""The four functions the assignment asks for, composed from the page objects.

TypeScript signature in the spec      ->  Python method here
-----------------------------------------------------------------
(auth)                                 ->  authenticate()
searchItemsByNameUnderPrice            ->  search_items_by_name_under_price()
addItemsToCart                         ->  add_items_to_cart()
assertCartTotalNotExceeds              ->  assert_cart_total_not_exceeds()
"""
from __future__ import annotations

import logging
from typing import Any

import allure
from playwright.sync_api import Page

from pages import CartPage, ItemPage, LoginPage, SearchPage
from utils.errors import BudgetExceededError
from utils.overlays import install_overlay_handlers

log = logging.getLogger(__name__)


class ShoppingFlow:
    def __init__(self, page: Page, config: dict[str, Any]):
        self.page = page
        self.config = config
        install_overlay_handlers(page)
        self.login_page = LoginPage(page, config)
        self.search_page = SearchPage(page, config)
        self.item_page = ItemPage(page, config)
        self.cart_page = CartPage(page, config)

    def authenticate(self) -> str:  # the LoginPage step already names this in the report
        return self.login_page.login_or_guest()

    @allure.step("searchItemsByNameUnderPrice({query}, {max_price}, {limit})")
    def search_items_by_name_under_price(self, query: str, max_price: float, limit: int = 5) -> list[str]:
        self.search_page.search(query)
        self.search_page.apply_max_price_filter(max_price)
        urls = self.search_page.collect_item_urls(max_price, limit)
        allure.attach("\n".join(urls) or "(none)", name=f"collected_urls ({len(urls)})",
                      attachment_type=allure.attachment_type.TEXT)
        return urls

    @allure.step("addItemsToCart({urls})")
    def add_items_to_cart(self, urls: list[str]) -> None:
        search_url = self.page.url
        for i, url in enumerate(urls, start=1):
            self.item_page.add_to_cart(url, i)
            with allure.step("Return to search results"):
                self.search_page.navigate(search_url)

    @allure.step("assertCartTotalNotExceeds({budget_per_item}, {items_count})")
    def assert_cart_total_not_exceeds(self, budget_per_item: float, items_count: int) -> None:
        self.cart_page.open_cart()
        total = self.cart_page.read_subtotal()
        self.cart_page.screenshot("cart_total", full_page=True)
        threshold = budget_per_item * items_count
        with allure.step(f"Verify subtotal {total.amount:.2f} <= {threshold:.2f}"):
            log.info("Cart total %.2f vs threshold %.2f", total.amount, threshold)
            if total.amount > threshold:
                raise BudgetExceededError(total.amount, total.currency, budget_per_item, items_count)
