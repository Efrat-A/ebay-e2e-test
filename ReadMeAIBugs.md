# AI-generated test - code review

## The code under review

```python
from playwright.sync_api import sync_playwright
from selenium import webdriver
import time

def test_search_functionality():
    browser = sync_playwright().start().chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")
    time.sleep(2)
    search_box = page.locator("#search")
    search_box.fill("playwright testing")
    page.locator(".button").click()
    time.sleep(3)
    results = page.locator(".result-item")
    browser.close()
```

## Issues found

### 1. The test has no assertion - it can never fail on wrong behaviour
`results = page.locator(".result-item")` only *builds* a locator. Playwright locators are lazy: nothing is queried until an action or assertion runs. So the line does nothing, and the test passes even if the search returns zero results or shows an error page.

**Fix:** assert on the results with a web-first assertion.
```python
results = page.locator(".result-item")
expect(results.first).to_be_visible()
assert results.count() > 0, "Search returned no results"
```

### 2. Playwright is started and never stopped (resource leak)
`sync_playwright().start()` launches the Playwright driver process, but the returned object is discarded, so `.stop()` can never be called. Each run leaves a driver process behind; in a suite this accumulates and can hang CI.

**Fix:** use the context manager, which stops Playwright automatically.
```python
with sync_playwright() as p:
    browser = p.chromium.launch()
```

### 3. `browser.close()` is not guaranteed to run
If any step fails (`fill`, `click`, timeout), the exception skips `browser.close()` and the browser stays open.

**Fix:** close in `finally` (or use a pytest fixture with `yield`).
```python
try:
    ...
finally:
    browser.close()
```

### 4. Hard-coded sleeps (`time.sleep(2)`, `time.sleep(3)`)
Fixed waits make the test slow when the page is fast and flaky when it is slow. Playwright already auto-waits for elements to be actionable before `fill`/`click`, and `expect()` retries until the condition holds.

**Fix:** delete both sleeps; rely on auto-waiting and `expect(...)`. If a navigation must finish, use `page.wait_for_load_state()`.

### 5. Unused Selenium import - mixing two frameworks
`from selenium import webdriver` is never used. It adds a dependency that may not be installed (the test fails at import with `ModuleNotFoundError` before running) and suggests confusion between Selenium and Playwright APIs - a typical AI-generation artifact.

**Fix:** remove the line.

### 6. Fragile, ambiguous locators
`.button` matches *any* element with that class - Playwright's strict mode will throw if several match, or it may click the wrong button. `#search` may point to a container rather than the input.

**Fix:** user-facing locators.
```python
page.get_by_role("searchbox").fill(query)
page.get_by_role("button", name="Search").click()
```

### 7. Hard-coded URL and data
`https://example.com` (which has no search at all) and `"playwright testing"` are embedded in the test, so it can't run against another environment or data set.

**Fix:** take them from config / test data (fixture or parametrize).

## Corrected version

```python
import pytest
from playwright.sync_api import sync_playwright, expect


@pytest.mark.parametrize("query", ["playwright testing"])
def test_search_functionality(base_url, query):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(base_url)
            page.get_by_role("searchbox").fill(query)
            page.get_by_role("button", name="Search").click()

            results = page.locator(".result-item")
            expect(results.first).to_be_visible()
            assert results.count() > 0, f"No results for '{query}'"
        finally:
            browser.close()
```
