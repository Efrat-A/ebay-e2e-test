# Bot protection & CAPTCHA handling

eBay's public site rate-limits and challenges automated traffic (HTTP 403/429, CAPTCHA, error pages). This covers how the framework detects and reports that, and why it does not try to get around it.

## Detection & retries

After every navigation the framework waits for the page to load and checks for an error page (HTTP 403/429/5xx, a title/heading such as 'Access Denied' / 'Something went wrong', or eBay's 'Please go back and try again' text). It loads the original URL again with growing pauses (`retry.page_error_retries`, `retry.page_error_backoff_sec`), and only then fails with a clear `[BLOCKED]` or `[PAGE ERROR]` message plus a screenshot. CAPTCHA pages are never refreshed or bypassed - they fail immediately as `[BOT CHALLENGE]`. `slow_mo_ms` (default 500 ms) slows the pace to make blocking less likely.

## Login CAPTCHA fallback

eBay sign-in uses CAPTCHA, which this project does not bypass: in the `local` profile a CAPTCHA falls back to guest (recorded as `auth_mode` in the report); in `ci` (`guest_fallback_on_challenge: false`) it fails the run as *Blocked by bot protection*.

## Treating it as skipped instead of failed/broken

By default a `BotChallengeError`/`AccessBlockedError` (CAPTCHA, HTTP 403/429) reports as *broken* - a real result, visible in the Allure Categories tab. Set `skip_on_bot_protection: true` in a config profile, or `SKIP_ON_BOT_PROTECTION=true` as an env var, to instead report it as **skipped** - useful when you want a run's exit code/summary to stay clean despite eBay rate-limiting, without silently hiding the cause (the skip reason still states `[BOT PROTECTION] <original message>`). The conversion happens in `conftest.py`'s `pytest_runtest_makereport` hook, regardless of whether the challenge hit during login (setup) or mid-scenario (call) - screenshots are still attached either way, since those are captured where the error is raised, not by this hook.

## Why not bypass it?

There is no documented header or flag that whitelists automation on the public eBay site, and evading the protection (header spoofing, proxies, stealth plugins) is not something a test suite should do. In a real project this is solved with the site owner: a QA bypass header/token on a staging environment, allow-listed CI IPs, or a dedicated test environment - which is what the [eBay Sandbox](https://developer.ebay.com/tools/sandbox) offers (test users, test money), although it covers only part of the site and eBay recommends production for testing search.

eBay may change its DOM or rate-limit automated traffic independently of CAPTCHA; selectors are kept in the page objects so they are easy to update.
