import allure
import pytest

from flows import ShoppingFlow
from utils.errors import no_items_message


@allure.epic("eBay")
@allure.feature("Shopping cart")
@allure.story("Search under price -> add to cart -> budget check")
@allure.severity(allure.severity_level.CRITICAL)
@allure.description(
    "Searches eBay for items priced at or under max_price (with paging), adds them to the "
    "cart with random variants, and verifies the cart subtotal does not exceed "
    "budget_per_item x number of items."
)
@pytest.mark.e2e
def test_cart_total_within_budget(page, config, scenario):
    allure.dynamic.title(
        f"{scenario['id']}: '{scenario['query']}' x{scenario['limit']} under {scenario['max_price']}"
    )
    for key in ("query", "max_price", "limit", "budget_per_item"):
        allure.dynamic.parameter(key, scenario[key])

    flow = ShoppingFlow(page, config)

    flow.authenticate()
    urls = flow.search_items_by_name_under_price(
        scenario["query"], scenario["max_price"], scenario["limit"]
    )
    if not urls:
        pytest.skip(no_items_message(scenario["query"], scenario["max_price"]))

    flow.add_items_to_cart(urls)
    flow.assert_cart_total_not_exceeds(scenario["budget_per_item"], len(urls))
