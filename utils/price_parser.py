"""Turns eBay price strings into numbers.

Handles currency symbols/codes ($, ₪, ILS, US $, €), thousands separators,
ranges ("$10.00 to $20.00") and non-price text ("Free shipping", "See price").
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_NUMBER = re.compile(r"\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")
_CURRENCY = re.compile(r"(US\s?\$|C\s?\$|AU\s?\$|ILS|NIS|USD|EUR|GBP|\$|₪|€|£)", re.I)


@dataclass(frozen=True)
class Price:
    amount: float
    currency: Optional[str]


def _to_float(token: str) -> float:
    return float(token.replace(",", "").replace(" ", ""))


def parse_price(text: str | None, range_strategy: str = "max") -> Optional[Price]:
    """Return a Price, or None when the text holds no price.

    range_strategy: "max" (default, safe for budget checks) or "min".
    """
    if not text:
        return None
    cleaned = text.replace("\xa0", " ").strip()
    numbers = [_to_float(n) for n in _NUMBER.findall(cleaned)]
    if not numbers:
        return None
    currency_match = _CURRENCY.search(cleaned)
    currency = currency_match.group(1).upper().replace(" ", "") if currency_match else None

    if len(numbers) > 1 and re.search(r"\bto\b|-|–", cleaned):
        amount = max(numbers) if range_strategy == "max" else min(numbers)
    else:
        amount = numbers[0]
    return Price(amount=amount, currency=currency)
