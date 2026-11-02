import pytest

from utils.price_parser import parse_price


@pytest.mark.parametrize("text, amount, currency", [
    ("$12.99", 12.99, "$"),
    ("US $1,234.50", 1234.50, "US$"),
    ("ILS 45.00", 45.00, "ILS"),
    ("₪199.90", 199.90, "₪"),
    ("$10.00 to $20.00", 20.00, "$"),
    ("ILS 1 299.00", 1299.00, "ILS"),
])
def test_parses_prices(text, amount, currency):
    price = parse_price(text)
    assert price.amount == pytest.approx(amount)
    assert price.currency == currency


def test_range_min_strategy():
    assert parse_price("$10.00 to $20.00", range_strategy="min").amount == 10.00


@pytest.mark.parametrize("text", [None, "", "Free shipping", "See price"])
def test_non_prices_return_none(text):
    assert parse_price(text) is None
