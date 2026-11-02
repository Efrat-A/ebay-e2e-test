from __future__ import annotations

import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import allure

from pages.base_page import BasePage
from utils.price_parser import parse_price
from utils.retry import retry

log = logging.getLogger(__name__)


class SearchPage(BasePage):
    # eBay serves two result-card layouts; the XPaths cover both.
    RESULT_CARDS_XPATH = (
        "//ul[contains(@class,'srp-results')]/li"
        "[contains(@class,'s-item') or contains(@class,'s-card')]"
    )
    PRICE_XPATH = ".//*[contains(@class,'s-item__price') or contains(@class,'s-card__price')]"
    LINK_XPATH = ".//a[contains(@href,'/itm/')]"

    SEARCH_INPUT = ["#gh-ac", "input[name='_nkw']", "input[aria-label*='Search']"]
    SEARCH_BUTTON = ["#gh-search-btn", "#gh-btn", "button[type='submit'][value='Search']"]
    MAX_PRICE_INPUT = ["input[aria-label*='Maximum Value']", "input[name='_udhi']"]
    PRICE_SUBMIT = ["button[aria-label*='Submit price range']", "button[type='submit']:near(input[name='_udhi'])"]
    NEXT_PAGE = ["a.pagination__next:not([aria-disabled='true'])", "a[aria-label='Go to next search page']"]

    # retry OUTSIDE the step: allure.step reads parameter names from the function it wraps
    @retry(attempts=2, delay_sec=1)
    @allure.step("Search for {query}")
    def search(self, query: str) -> None:
        self.open(self.config["base_url"])
        self.smart("search box", self.SEARCH_INPUT).resolve().fill(query)
        self.smart("search button", self.SEARCH_BUTTON).resolve().click()
        self.page.wait_for_load_state("domcontentloaded")
        self.ensure_no_bot_challenge()

    @allure.step("Filter by max price {max_price}")
    def apply_max_price_filter(self, max_price: float) -> None:
        """Use the site's price filter if it's on the page, else the URL param eBay uses."""
        field = self.smart("max price field", self.MAX_PRICE_INPUT).try_resolve(timeout_ms=3000)
        submit = self.smart("price submit", self.PRICE_SUBMIT).try_resolve(timeout_ms=1000) if field else None
        if field and submit:
            field.fill(str(max_price))
            submit.click()
            allure.dynamic.parameter("filter_method", "UI")
        else:
            log.info("Price filter UI not found - using _udhi URL parameter")
            self.navigate(self._with_param(self.page.url, "_udhi", str(max_price)))
            allure.dynamic.parameter("filter_method", "URL _udhi")
        self.page.wait_for_load_state("domcontentloaded")

    @allure.step("Collect up to {limit} items priced <= {max_price}")
    def collect_item_urls(self, max_price: float, limit: int) -> list[str]:
        urls: list[str] = []
        page_no = 1
        while len(urls) < limit:
            urls += self._scan_results_page(page_no, max_price, limit - len(urls), seen=set(urls))
            if len(urls) >= limit or not self._go_next_page():
                break
            page_no += 1
        log.info("Collected %d item(s) under %s", len(urls), max_price)
        return urls

    @allure.step("Scan results page {page_no}")
    def _scan_results_page(self, page_no: int, max_price: float, needed: int, seen: set[str]) -> list[str]:
        found: list[str] = []
        cards = self.page.locator(f"xpath={self.RESULT_CARDS_XPATH}")
        strategy = self.config.get("price_range_strategy", "max")
        for i in range(cards.count()):
            if len(found) >= needed:
                break
            card = cards.nth(i)
            price_el = card.locator(f"xpath={self.PRICE_XPATH}").first
            link_el = card.locator(f"xpath={self.LINK_XPATH}").first
            if price_el.count() == 0 or link_el.count() == 0:
                continue  # ad slots / "shop on eBay" placeholders
            price = parse_price(price_el.inner_text(), strategy)
            url = (link_el.get_attribute("href") or "").split("?")[0]
            if price and price.amount <= max_price and url and url not in seen:
                found.append(url)
                seen.add(url)
        log.info("Page %d: %d matching item(s)", page_no, len(found))
        return found

    def _go_next_page(self) -> bool:
        nxt = self.smart("next page", self.NEXT_PAGE).try_resolve(timeout_ms=2000)
        if not nxt:
            return False
        with allure.step("Go to next results page"):
            nxt.click()
            self.page.wait_for_load_state("domcontentloaded")
        return True

    @staticmethod
    def _with_param(url: str, key: str, value: str) -> str:
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        query[key] = value
        return urlunsplit(parts._replace(query=urlencode(query)))
