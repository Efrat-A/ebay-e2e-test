# eBay E2E Automation

End-to-end scenario on eBay: **search under a max price → add items to cart → assert the cart total is within budget**.
Python · Playwright · pytest · Allure · POM · OOP · Data-Driven.

## Prerequisites

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) (package/venv manager; `brew install uv`)
- Java (only for building the Allure report; `brew install openjdk`)
- `make`, `curl`

No global Allure install is needed: `make install` downloads the Allure CLI into `.tools/` inside the project.

## Setup

```bash
make install        # uv-managed .venv + packages + browsers + local Allure CLI + .env from template
```

## Run

```bash
make run            # E2E -> build report -> open it in the browser
make e2e            # E2E scenarios only, profile "local" (headless by default)
make ci             # headless, trace always on
make unit           # fast unit tests (no browser)
make test           # everything
make help           # list all targets
```

Options: `make e2e PROFILE=ci`, `BROWSER=firefox make e2e` (also `webkit`). `make install` downloads all three browser binaries; if you only ran `uv run playwright install chromium` yourself (or skipped `make install`), Firefox/WebKit will fail to launch until you also run `uv run playwright install firefox webkit` - this is a common cause of "nothing happens" when setting `BROWSER=firefox` from an IDE run configuration.

Profiles can inherit with `extends:`. `realistic_ua` (extends `local`) is an experiment with a fixed desktop-Chrome User-Agent, US locale/timezone and a Full-HD viewport: `make e2e PROFILE=realistic_ua`.

**Headless or visible browser** - `pytest.ini` sets `headless = true`, so tests run headless by default.
Override per run with `pytest --headed` / `pytest --headless` or `HEADLESS=false`.
Precedence: CLI flag > `HEADLESS` env var > `pytest.ini` > config profile. `make ci` always runs headless.
Direct pytest also works, e.g. `uv run pytest --data=data/other.json`.

## Reports

See [docs/REPORTS.md](docs/REPORTS.md) - report formats, failure categories, and screenshots.

## Architecture

```
config/config.yaml      environment profiles (local / ci): URLs, browser, timeouts, retries
config/allure/          Allure categories.json
data/test_data.json     test scenarios (query, max_price, limit, budget_per_item)
pages/                  Page Objects - one class per page, locators live only here
  base_page.py          navigation, popup dismissal, screenshots
  login_page.py         user login or guest fallback
  search_page.py        search, price filter, XPath result scan, paging
  item_page.py          random variant selection, add to cart
  cart_page.py          read subtotal
flows/shopping_flow.py  the 4 required functions, composed from the pages
utils/
  browser_logs.py       console / page errors / HTTP >= 400 -> logging + failure attachment
  errors.py             tagged domain errors (feed the Allure categories)
  smart_locator.py      multi-selector fallback for eBay's parallel layouts
  price_parser.py       "$10 to $20", "ILS 1,299.00", "Free shipping" -> number
  retry.py              retry decorator for flaky UI steps
  config_loader.py      YAML + .env + env-var overrides
tests/e2e/conftest.py   `flow` fixture: authentication (user or guest) before every E2E test
tests/e2e/test_ebay_e2e.py  data-driven E2E test (no locators, no waits, no login - only the scenario)
tests/unit/             unit tests: price parser, failure categories
conftest.py             browser/page fixtures, scenario parametrization, trace & failure screenshot
```

Layering: **test → flow → page objects → utils**. Login runs in the `flow` fixture, so in Allure it appears under *Set up* and a login problem is never mistaken for a scenario failure. Tests read like the scenario; pages own locators; utils hold logic that doesn't depend on a page.

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
- **Overlays**: the ship-to location dialog and the cookie banner are handled by `page.add_locator_handler` (`utils/overlays.py`), so they are dealt with whenever they block an action - even when they load late.
- **Retries** on flaky steps; other popups are dismissed best-effort.

## Assumptions & limitations

- **Authentication**: with no credentials in `.env` (default) the test runs as **guest** - the cart works without an account. When credentials *are* set, any login failure raises `LoginFailedError`.
- **Currency**: comparisons are numeric in whatever currency eBay displays (e.g. ILS when browsing from Israel). `max_price` and `budget_per_item` must be in that same currency.
- **Price ranges**: an item listed as "$10 to $20" is treated as $20 by default, so the selected variant can never push the cart over budget.
- **Cart total** is the subtotal shown on the cart page (before shipping/tax).
- **Bot protection & CAPTCHA**: eBay rate-limits and challenges automated traffic - see [docs/BOT_PROTECTION.md](docs/BOT_PROTECTION.md) for detection, retries, the login fallback, and why it's never bypassed.

## Future improvements

See [docs/FUTURE_IMPROVEMENTS.md](docs/FUTURE_IMPROVEMENTS.md).
