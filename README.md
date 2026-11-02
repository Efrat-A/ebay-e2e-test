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

**Headless or visible browser** - `pytest.ini` sets `headless = false`, so the browser window is shown by default.
Override per run with `pytest --headless` / `pytest --headed` or `HEADLESS=true`.
Precedence: CLI flag > `HEADLESS` env var > `pytest.ini` > config profile. `make ci` always runs headless.
Direct pytest also works, e.g. `.venv/bin/pytest --data=data/other.json`.

## Reports

```bash
make allure-generate # builds reports/allure-report/index.html
make open           # opens it
```

The report is generated as a **single self-contained HTML file**, so it opens straight from disk - no `allure serve`, no web server.

Every run produces:
- **Allure report** with a step per function, a screenshot per item added, the cart screenshot and the collected URLs
- **Browser console log** attached to failed tests: console messages, uncaught page errors and HTTP responses >= 400 (only when there were any). The same lines go to Python logging under the `browser` logger - see them live with `pytest --log-cli-level=DEBUG`.
- **JUnit XML** at `reports/junit.xml` (for CI)
- **Playwright trace** at `reports/traces/*.zip` (on failure, or always with `--profile=ci`). Open with `playwright show-trace <file>`.

## Failure categories & error messages

Every framework error has a tagged, self-explanatory message, for example:

```
[BUDGET EXCEEDED] Cart subtotal 512.40 ILS is above the allowed 220.00 x 2 item(s) = 440.00 ILS (over by 72.40 ILS).
[ELEMENT NOT FOUND] 'Add to cart button' was not found on https://www.ebay.com/itm/... within 5000 ms. Tried selectors: [...]
```

`config/allure/categories.json` (copied into the results automatically) groups failures in the Allure *Categories* tab:

| Category | Status | Meaning |
|---|---|---|
| Cart over budget (product defect) | failed | the business rule under test failed |
| Element not found (page layout changed) | broken | update a locator |
| Blocked by bot protection | broken | HTTP 403/429 or CAPTCHA - environmental; slow down via `slow_mo_ms` |
| Login failed | broken | wrong credentials / changed sign-in page |
| Add to cart not confirmed | broken | out of stock, variant issue |
| Price could not be parsed | broken | new price format |
| Timeouts | broken | slow page / network |
| No items in price range | skipped | 0 results is a valid outcome |
| Other assertion failures / Unexpected errors | failed / broken | anything else |

Categories are mutually exclusive (verified by `tests/unit/test_categories.py`), so each failure is counted once.

Every page-object action is an `@allure.step`, so the report shows the full flow as a step tree: spec function -> page action -> sub-step, with screenshots attached at the step where they were taken.

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

- **Authentication**: with no credentials in `.env` (default) the test runs as **guest** - the cart works without an account. When credentials *are* set, any login failure raises `LoginFailedError`. eBay sign-in uses CAPTCHA, which this project does not bypass: in the `local` profile a CAPTCHA falls back to guest (recorded as `auth_mode` in the report); in `ci` (`guest_fallback_on_challenge: false`) it fails the run as *Blocked by bot protection*.
- **Currency**: comparisons are numeric in whatever currency eBay displays (e.g. ILS when browsing from Israel). `max_price` and `budget_per_item` must be in that same currency.
- **Price ranges**: an item listed as "$10 to $20" is treated as $20 by default, so the selected variant can never push the cart over budget.
- **Cart total** is the subtotal shown on the cart page (before shipping/tax).
- **Bot protection**: eBay may answer automated traffic with HTTP 403. Every navigation checks the status code and fails with a clear `[BLOCKED]` message (plus a screenshot) instead of a confusing locator timeout. `slow_mo_ms` (default 500 ms) slows the pace to reduce this.
- eBay may change its DOM or rate-limit automated traffic; selectors are kept in the page objects so they are easy to update.

## Future improvements

See [FUTURE_IMPROVEMENTS.md](FUTURE_IMPROVEMENTS.md).
