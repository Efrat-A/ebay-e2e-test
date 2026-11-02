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

    @retry(attempts=2, delay_sec=1)
    def search(self, query: str) -> None:
        with allure.step(f"Search for '{query}'"):
            self.open(self.config["base_url"])
            self.smart("search_input", self.SEARCH_INPUT).resolve().fill(query)
            self.smart("search_button", self.SEARCH_BUTTON).resolve().click()
            self.page.wait_for_load_state("domcontentloaded")

    def apply_max_price_filter(self, max_price: float) -> None:
        """Use the site's price filter if it's on the page, else the URL param eBay uses."""
        with allure.step(f"Apply max price filter <= {max_price}"):
            field = self.smart("max_price", self.MAX_PRICE_INPUT).try_resolve(timeout_ms=3000)
            submit = self.smart("price_submit", self.PRICE_SUBMIT).try_resolve(timeout_ms=1000) if field else None
            if field and submit:
                field.fill(str(max_price))
                submit.click()
            else:
                log.info("Price filter UI not found - using _udhi URL parameter")
                self.page.goto(self._with_param(self.page.url, "_udhi", str(max_price)))
            self.page.wait_for_load_state("domcontentloaded")

    def collect_item_urls(self, max_price: float, limit: int) -> list[str]:
        urls: list[str] = []
        page_no = 1
        while len(urls) < limit:
            with allure.step(f"Scan results page {page_no}"):
                urls += self._scan_current_page(max_price, limit - len(urls), seen=set(urls))
            if len(urls) >= limit or not self._go_next_page():
                break
            page_no += 1
        log.info("Collected %d item(s) under %s", len(urls), max_price)
        return urls

    def _scan_current_page(self, max_price: float, needed: int, seen: set[str]) -> list[str]:
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
            href = link_el.get_attribute("href") or ""
            url = href.split("?")[0]
            if price and price.amount <= max_price and url and url not in seen:
                found.append(url)
                seen.add(url)
        return found

    def _go_next_page(self) -> bool:
        nxt = self.smart("next_page", self.NEXT_PAGE).try_resolve(timeout_ms=2000)
        if not nxt:
            return False
        nxt.click()
        self.page.wait_for_load_state("domcontentloaded")
        return True

    @staticmethod
    def _with_param(url: str, key: str, value: str) -> str:
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        query[key] = value
        return urlunsplit(parts._replace(query=urlencode(query)))
