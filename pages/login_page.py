from __future__ import annotations

import logging

import allure

from pages.base_page import BasePage

log = logging.getLogger(__name__)


class LoginPage(BasePage):
    """Authentication step.

    eBay protects sign-in with bot detection / CAPTCHA, which automation must not
    bypass. So: if EBAY_USERNAME/EBAY_PASSWORD are set we attempt a normal login
    and stop if a challenge appears; otherwise we continue as a guest (the cart
    works without an account).
    """

    def login_or_guest(self) -> str:
        creds = self.config.get("credentials") or {}
        if not creds.get("username") or not creds.get("password"):
            log.info("No credentials configured - continuing as guest")
            allure.dynamic.parameter("auth_mode", "guest")
            return "guest"
        with allure.step("Login with configured account"):
            self.open("https://signin.ebay.com")
            self.smart("username", ["#userid", "input[name='userid']"]).resolve().fill(creds["username"])
            self.smart("continue", ["#signin-continue-btn", "button:has-text('Continue')"]).resolve().click()
            if self._challenge_present():
                log.warning("Bot challenge shown - falling back to guest mode")
                self.screenshot("login_challenge")
                return "guest"
            self.smart("password", ["#pass", "input[name='pass']"]).resolve().fill(creds["password"])
            self.smart("sign_in", ["#sgnBt", "button:has-text('Sign in')"]).resolve().click()
            self.page.wait_for_load_state("domcontentloaded")
            allure.dynamic.parameter("auth_mode", "user")
            return "user"

    def _challenge_present(self) -> bool:
        return self.smart("captcha", ["iframe[src*='captcha']", "#captcha_loading", "text=/verify.*human/i"]) \
            .try_resolve(timeout_ms=2500) is not None
