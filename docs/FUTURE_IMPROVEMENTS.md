# Future Improvements

Items intentionally left out of the 3-4 hour scope, ordered by value.

## Reporting

### Migrate to Allure 3
Allure 3 is a TypeScript rewrite of the report generator. It runs on Node (`npx allure generate`) instead of Java, which removes the JDK prerequisite for building reports and makes the Makefile simpler. It reads the same `allure-results` produced by `allure-pytest`, so no test code changes. To evaluate before switching: maturity of the new report UI, single-file output support, and categories/history parity with Allure 2.

### History and trends
Copy `reports/allure-report/history/` into `reports/allure-results/` before each `allure generate`, so the report shows pass-rate trends, duration trends and flaky-test markers across runs. In CI this means persisting the history folder as a build artifact or on the published report branch.

### Environment panel
Write `environment.properties` into the results folder (profile, browser, base URL, Python/Playwright versions, auth mode) so every report states what it was run against.

### Executor info and published reports
Add `executor.json` (build number, CI link) and publish the HTML report from CI (e.g. GitHub Pages) so a reviewer can open the latest run from a link.

## Test environment

### Run against a test environment instead of production
eBay's bot protection is the main source of flakiness (HTTP 403, "Please go back and try again", CAPTCHA). The robust fix is organisational, not technical: run against an environment where automation is expected - a staging site with a QA bot-protection bypass header/token, allow-listed CI IP addresses, or eBay's [Sandbox](https://developer.ebay.com/tools/sandbox) (test users and test money; covers a subset of the site, so search scenarios would need verifying there). The base URL and cart URL are already in the config profiles, so this is a new profile, not a code change.

### Log in once per run and share the session
Authenticate once in a session-scoped fixture, save cookies/localStorage with Playwright's `storage_state`, and start every test context from it (optionally reuse the file across runs while it is fresh). Fewer logins and first-visit pages mean fewer bot-protection triggers. Prerequisites before enabling it:
- a shared session shares the cart, so every test must start by emptying the cart;
- with a real account the cart is stored server-side and survives between runs - use a dedicated test account only, never a personal one;
- keep the saved state file out of git (it contains session cookies) and expire it in CI.

## CI / execution

- **GitHub Actions workflow**: lint, unit tests on every push; E2E on a schedule and on demand; upload Allure results, traces and screenshots as artifacts.
- **Parallel runs**: `pytest-xdist` across scenarios and browsers. Needs one browser context per worker (already the case) and separate carts per worker.
- **Docker image** with Python, browsers and Java/Node pre-installed, so local and CI runs are identical.
- **Flaky-test policy**: `pytest-rerunfailures` limited to the *Timeouts* and *Bot protection* categories only, never to *Cart over budget*, so real defects are never retried away.

## Test robustness

- **Cart cleanup**: empty the cart before and after each scenario (guest carts persist via cookies); today each test uses a fresh browser context instead.
- **Network-level waits**: wait for the search/cart XHR responses instead of DOM load states where possible.
- **Locator health check**: a small smoke test that only verifies each page object's primary locators resolve, to detect eBay layout changes before the full scenario fails.
- **Currency normalisation**: convert prices to a single currency (or force a locale/ship-to country) so `max_price` and the budget are always compared in one currency.
- **Shipping-aware budget**: optional rule that includes shipping cost in the budget check.

## Code quality

- **Static checks**: `ruff` and `mypy` (type hints are already in place) via `make lint` and a pre-commit hook.
- **Typed configuration**: replace the config dict with a `pydantic` settings model to validate profiles on load.
- **Test data generation**: allow scenarios in YAML/CSV as well as JSON, and parametrize browser x scenario.
