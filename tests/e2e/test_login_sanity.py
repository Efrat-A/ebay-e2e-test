"""Lightweight sanity check for authentication alone - no search, no cart.

Runs fast and isolates login/guest-fallback problems from the full budget scenario, where a
login issue would otherwise only surface buried inside that test's "Set up" phase.
"""
import allure
import pytest


@allure.epic("eBay")
@allure.feature("Authentication")
@allure.story("Login or guest fallback")
@allure.severity(allure.severity_level.CRITICAL)
@allure.description(
    "Sanity check: authenticate only (no search/cart). Confirms the session reaches a usable "
    "state - guest or signed in - and is not stuck on a bot-challenge or error page."
)
@pytest.mark.e2e
def test_login_or_guest_succeeds(flow):
    allure.dynamic.title(f"Authenticate against eBay (profile '{flow.config['profile']}')")
    assert flow.auth_mode in ("guest", "user"), f"Unexpected auth_mode: {flow.auth_mode!r}"
    flow.login_page.ensure_no_bot_challenge()
