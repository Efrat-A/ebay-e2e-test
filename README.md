# eBay E2E Automation

End-to-end scenario on eBay: **search under a max price → add items to cart → assert the cart total is within budget**.
Python · Playwright · pytest · Allure · POM · OOP · Data-Driven.

## Prerequisites

- Python 3.10+
- Java (only for building the Allure report; `brew install openjdk`)
- `make`, `curl`

No global Allure install is needed: `make install` downloads the Allure CLI into `.tools/` inside the project.

## Setup

```bash
make install        # .venv + packages + Chromium + local Allure CLI + .env from template
```

## Run

```bash
make run            # E2E -> build report -> open it in the browser
make e2e            # E2E scenarios only, profile "local" (browser visible)
make ci             # headless, trace always on
make unit           # fast unit tests (no browser)
make test           # everything
make help           # list all targets
```

Options: `make e2e PROFILE=ci`, `BROWSER=firefox make e2e`.
Direct pytest also works, e.g. `.venv/bin/pytest --data=data/other.json`.

## Reports

```bash
make allure-generate # builds reports/allure-report/index.html
make open           # opens it
```

The report is generated as a **single self-contained HTML file**, so it opens straight from disk - no `allure serve`, no web server.

Every run produces:
- **Allure report** with a step per function, a screenshot per item added, the cart screenshot and the collected URLs
- **JUnit XML** at `reports/junit.xml` (for CI)
- **Playwright trace** at `reports/traces/*.zip` (on failure, or always with `--profile=ci`). Open with `playwright show-trace <file>`.

## Architecture

```
config/config.yaml      environment profiles (local / ci): URLs, browser, timeouts, retries
data/test_data.json     test scenarios (query, max_price, limit, budget_per_item)
pages/                  Page Objects - one class per page, locators live only here
  base_page.py          navigation, popup dismissal, screenshots
  login_page.py         user login or guest fallback
  search_page.py        search, price filter, XPath result scan, paging
  item_page.py          random variant selection, add to cart
  cart_page.py          read subtotal
flows/shopping_flow.py  the 4 required functions, composed from the pages
utils/
  smart_locator.py      multi-selector fallback for eBay's parallel layouts
  price_parser.py       "$10 to $20", "ILS 1,299.00", "Free shipping" -> number
  retry.py              retry decorator for flaky UI steps
  config_loader.py      YAML + .env + env-var overrides
tests/test_ebay_e2e.py  data-driven E2E test (no locators, no waits - only the flow)
tests/unit/             unit tests for the price parser
conftest.py             browser/page fixtures, scenario parametrization, trace & failure screenshot
```

Layering: **test → flow → page objects → utils**. Tests read like the scenario; pages own locators; utils hold logic that doesn't depend on a page.

| Spec function (TypeScript)       | Python                                   |
|----------------------------------|------------------------------------------|
| authentication                   | `ShoppingFlow.authenticate()`            |
| `searchItemsByNameUnderPrice`    | `search_items_by_name_under_price()`     |
| `addItemsToCart`                 | `add_items_to_cart()`                    |
| `assertCartTotalNotExceeds`      | `assert_cart_total_not_exceeds()`        |

## Robustness

- **Smart locators**: each element has several candidate selectors; the first visible one wins.
- **Price filter**: uses the on-page max-price filter when present, otherwise eBay's `_udhi` URL parameter.
- **XPath result scan**: covers both `s-item` and `s-card` result layouts, skips ad/placeholder cards.
- **Paging**: continues to "Next" until `limit` items are found or pages run out; returns fewer (even 0) otherwise.
- **Variants**: random enabled option for both native `<select>` and listbox-style pickers.
- **Price parsing**: currencies, thousands separators, ranges (configurable `max`/`min`), non-price text.
- **Retries** on flaky steps; popups are dismissed best-effort.

## Assumptions & limitations

- **Authentication**: eBay sign-in uses bot detection/CAPTCHA, which this project does not bypass. With no credentials (default) the test runs as **guest**; if a challenge appears during login it falls back to guest.
- **Currency**: comparisons are numeric in whatever currency eBay displays (e.g. ILS when browsing from Israel). `max_price` and `budget_per_item` must be in that same currency.
- **Price ranges**: an item listed as "$10 to $20" is treated as $20 by default, so the selected variant can never push the cart over budget.
- **Cart total** is the subtotal shown on the cart page (before shipping/tax).
- eBay may change its DOM or rate-limit automated traffic; selectors are kept in the page objects so they are easy to update.
