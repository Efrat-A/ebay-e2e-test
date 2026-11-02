"""Domain errors with tagged, human-readable messages.

Every message starts with a [TAG] so that:
  * a reader of the log understands the failure without opening the code, and
  * Allure groups failures by cause (see config/allure/categories.json).
"""
from __future__ import annotations

from typing import Sequence


class AutomationError(Exception):
    """Base class for framework errors (reported as *broken* in Allure)."""


class ElementNotFoundError(AutomationError):
    def __init__(self, name: str, url: str, selectors: Sequence[str], timeout_ms: int):
        super().__init__(
            f"[ELEMENT NOT FOUND] '{name}' was not found on {url} within {timeout_ms} ms. "
            f"Tried selectors: {list(selectors)}. "
            f"The page layout may have changed - update the locator in the page object."
        )


class BotChallengeError(AutomationError):
    def __init__(self, url: str):
        super().__init__(
            f"[BOT CHALLENGE] eBay showed a CAPTCHA / human-verification page at {url}. "
            f"The framework does not bypass it - run as guest, slow down, or retry later."
        )


class PriceParseError(AutomationError):
    def __init__(self, raw_text: str, where: str):
        super().__init__(
            f"[PRICE PARSE] Could not read a price from '{raw_text}' ({where}). "
            f"Check the price locator or extend utils/price_parser.py for this format."
        )


class AddToCartError(AutomationError):
    def __init__(self, index: int, url: str, reason: str):
        super().__init__(
            f"[ADD TO CART] Item #{index} was not confirmed as added to the cart. "
            f"URL: {url}. Reason: {reason}"
        )


class BudgetExceededError(AssertionError):
    """A real product-level failure (reported as *failed* in Allure)."""

    def __init__(self, total: float, currency: str | None, budget_per_item: float,
                 items_count: int):
        threshold = budget_per_item * items_count
        cur = f" {currency}" if currency else ""
        super().__init__(
            f"[BUDGET EXCEEDED] Cart subtotal {total:.2f}{cur} is above the allowed "
            f"{budget_per_item:.2f} x {items_count} item(s) = {threshold:.2f}{cur} "
            f"(over by {total - threshold:.2f}{cur})."
        )


def no_items_message(query: str, max_price: float) -> str:
    return (f"[NO ITEMS] No results for '{query}' at or under {max_price} - "
            f"nothing to add to the cart (0 results is a valid outcome).")


class LoginFailedError(AutomationError):
    def __init__(self, username: str, reason: str):
        super().__init__(
            f"[LOGIN FAILED] Could not sign in as '{username}': {reason}. "
            f"Check EBAY_USERNAME / EBAY_PASSWORD in .env, or leave them empty to run as guest."
        )


class AccessBlockedError(AutomationError):
    def __init__(self, status: int, url: str, slow_mo_ms: int, attempts: int = 1):
        super().__init__(
            f"[BLOCKED] eBay responded HTTP {status} for {url} on all {attempts} attempt(s) "
            f"(page was refreshed with growing pauses in between) - most likely eBay's bot protection. "
            f"Note: try a slower pace by increasing slow_mo_ms in config/config.yaml "
            f"(current: {slow_mo_ms} ms), or wait a few minutes before re-running."
        )


class PageErrorError(AutomationError):
    def __init__(self, reason: str, url: str, attempts: int):
        super().__init__(
            f"[PAGE ERROR] eBay showed an error page ({reason}) for {url} on all {attempts} "
            f"attempt(s), even after refreshing. The site may be having issues - re-run later."
        )


class NetworkError(AutomationError):
    def __init__(self, url: str, detail: str):
        super().__init__(
            f"[NETWORK] Could not reach {url} ({detail}). This is a connectivity problem, "
            f"not a test failure - check the internet connection, VPN or proxy and re-run."
        )
