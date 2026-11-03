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

**Browsers**: e2e tests run on **both Chromium and Firefox by default** (each scenario x each browser). Pin to a single engine with `BROWSER=firefox make e2e` (also `webkit`). Options: `make e2e PROFILE=ci`. `make install` downloads all three browser binaries; if you only ran `uv run playwright install chromium` yourself (or skipped `make install`), Firefox/WebKit will fail to launch until you also run `uv run playwright install firefox webkit` - this is a common cause of "nothing happens" when setting `BROWSER=firefox` from an IDE run configuration.

Profiles can inherit with `extends:`. `realistic_ua` (extends `local`) is an experiment with a fixed desktop-Chrome User-Agent, US locale/timezone and a Full-HD viewport: `make e2e PROFILE=realistic_ua`.

## Reports

See [docs/REPORTS.md](docs/REPORTS.md) - report formats, failure categories, and screenshots.

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
