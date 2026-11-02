import allure
import pytest

from flows import ShoppingFlow


@allure.feature("eBay shopping")
@allure.story("Search under price -> add to cart -> budget check")
@pytest.mark.e2e
def test_cart_total_within_budget(page, config, scenario):
    allure.dynamic.title(scenario["id"])
    flow = ShoppingFlow(page, config)

    flow.authenticate()
    urls = flow.search_items_by_name_under_price(
        scenario["query"], scenario["max_price"], scenario["limit"]
    )
    if not urls:
        pytest.skip(f"No items under {scenario['max_price']} for '{scenario['query']}' (0 is a valid result)")

    flow.add_items_to_cart(urls)
    flow.assert_cart_total_not_exceeds(scenario["budget_per_item"], len(urls))
