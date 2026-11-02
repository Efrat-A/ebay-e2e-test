"""Every framework error must land in its own, readable Allure category.

Mirrors Allure 2: a result is placed in EVERY category whose matchedStatuses
contains its status and whose messageRegex matches the whole message. So the
categories must be mutually exclusive - each error must land in exactly one.
Messages are prefixed with the exception type, as allure-pytest records them.
"""
import json
import re
from pathlib import Path

import pytest

from utils.errors import (AccessBlockedError, AddToCartError, BotChallengeError, BudgetExceededError,
                          ElementNotFoundError, LoginFailedError, PageErrorError, PriceParseError,
                          no_items_message)

CATEGORIES = json.loads(
    (Path(__file__).resolve().parents[2] / "config" / "allure" / "categories.json").read_text()
)


def categorize(message: str, status: str) -> list[str]:
    return [cat["name"] for cat in CATEGORIES
            if status in cat.get("matchedStatuses", [])
            and (cat.get("messageRegex") is None or re.fullmatch(cat["messageRegex"], message))]


def as_recorded(error: BaseException) -> str:
    """How allure-pytest writes the message: '<module>.<Type>: <text>'."""
    cls = type(error)
    prefix = cls.__name__ if cls.__module__ == "builtins" else f"{cls.__module__}.{cls.__name__}"
    return f"{prefix}: {error}"


@pytest.mark.parametrize("error, status, expected", [
    (BudgetExceededError(512.4, "ILS", 220, 2), "failed", "Cart over budget (product defect)"),
    (ElementNotFoundError("Add to cart button", "https://www.ebay.com/itm/1", ["#a", "#b"], 5000),
     "broken", "Element not found (page layout changed)"),
    (BotChallengeError("https://www.ebay.com/splashui/challenge"), "broken", "Blocked by bot protection"),
    (AccessBlockedError(403, "https://www.ebay.com/itm/317727161471", 500), "broken", "Blocked by bot protection"),
    (PageErrorError("HTTP 503", "https://www.ebay.com/sch/i.html", 3), "broken", "eBay error page"),
    (AddToCartError(2, "https://www.ebay.com/itm/1", "out of stock"), "broken", "Add to cart not confirmed"),
    (LoginFailedError("efrat", "eBay says: 'wrong password'"), "broken", "Login failed"),
    (PriceParseError("See price", "cart subtotal"), "broken", "Price could not be parsed"),
    (TimeoutError("Timeout 30000ms exceeded.\n=== logs ==="), "broken", "Timeouts"),
    (AssertionError("assert 1 == 2"), "failed", "Other assertion failures"),
    (RuntimeError("boom"), "broken", "Unexpected errors"),
])
def test_error_lands_in_exactly_one_category(error, status, expected):
    assert categorize(as_recorded(error), status) == [expected]


def test_wrapped_locator_error_counts_once():
    inner = ElementNotFoundError("'added' confirmation", "https://www.ebay.com/itm/1", ["#x"], 10000)
    outer = AddToCartError(1, "https://www.ebay.com/itm/1", str(inner))
    assert categorize(as_recorded(outer), "broken") == ["Add to cart not confirmed"]


def test_no_items_skip_is_categorized():
    assert categorize(f"Skipped: {no_items_message('shoes', 5)}", "skipped") == ["No items in price range"]


def test_budget_message_is_self_explanatory():
    msg = str(BudgetExceededError(512.4, "ILS", 220, 2))
    assert msg == ("[BUDGET EXCEEDED] Cart subtotal 512.40 ILS is above the allowed "
                   "220.00 x 2 item(s) = 440.00 ILS (over by 72.40 ILS).")


def test_budget_error_is_a_test_failure_not_breakage():
    assert issubclass(BudgetExceededError, AssertionError)
