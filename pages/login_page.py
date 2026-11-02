from __future__ import annotations

import logging

import allure

from pages.base_page import BasePage
from utils.errors import BotChallengeError, ElementNotFoundError, LoginFailedError

log = logging.getLogger(__name__)


class LoginPage(BasePage):
    """Authentication step.

    * No credentials in .env  -> guest mode by design (the cart works without an account).
    * Credentials configured   -> a real login; any failure RAISES, so a wrong password
      or a changed sign-in page is never hidden.
    * CAPTCHA during login     -> raises BotChallengeError, unless the profile sets
      `guest_fallback_on_challenge: true`, in which case the run continues as guest
      and the fallback is recorded in the report.
    """

    USERNAME = ["#userid", "input[name='userid']"]
    CONTINUE = ["#signin-continue-btn", "button:has-text('Continue')"]
    PASSWORD = ["#pass", "input[name='pass']"]
    SIGN_IN = ["#sgnBt", "button:has-text('Sign in')"]
    ERROR_MESSAGE = "#signin-error-msg, #errormsg, [role='alert']"
    SIGNED_IN = ["#gh-ug", "button[aria-label^='Account' i]", "a[href*='signout']"]

    @allure.step("Authenticate (credentials if configured, otherwise guest)")
    def login_or_guest(self) -> str:
        creds = self.config.get("credentials") or {}
        if not creds.get("username") or not creds.get("password"):
            log.info("No credentials configured - continuing as guest")
            allure.dynamic.parameter("auth_mode", "guest")
            return "guest"
        try:
            self._login(creds["username"], creds["password"])
        except BotChallengeError as exc:
            if not self.config.get("guest_fallback_on_challenge", False):
                raise
            log.warning("%s Falling back to guest (guest_fallback_on_challenge=true).", exc)
            allure.dynamic.parameter("auth_mode", "guest (login blocked by CAPTCHA)")
            return "guest"
        allure.dynamic.parameter("auth_mode", "user")
        return "user"

    @allure.step("Sign in as {username}")
    def _login(self, username: str, password: str) -> None:
        self.open("https://signin.ebay.com")
        try:
            self.smart("username field", self.USERNAME).resolve().fill(username)
            self.smart("continue button", self.CONTINUE).resolve().click()
            self.ensure_no_bot_challenge()
            self._raise_if_error_shown(username)
            self.smart("password field", self.PASSWORD).resolve().fill(password)
            self.smart("sign-in button", self.SIGN_IN).resolve().click()
            self.page.wait_for_load_state("domcontentloaded")
            self.ensure_no_bot_challenge()
            self._raise_if_error_shown(username)
            self.smart("signed-in indicator", self.SIGNED_IN).resolve(timeout_ms=10000)
        except ElementNotFoundError as exc:
            self.screenshot("login_failed")
            raise LoginFailedError(username, f"sign-in flow did not complete ({exc})") from exc

    def _raise_if_error_shown(self, username: str) -> None:
        error = self.page.locator(self.ERROR_MESSAGE).first
        if error.count() and error.is_visible():
            self.screenshot("login_failed")
            raise LoginFailedError(username, f"eBay says: '{error.inner_text().strip()}'")
