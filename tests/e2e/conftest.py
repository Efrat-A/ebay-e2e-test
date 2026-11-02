"""E2E fixtures: every test here starts from an authenticated (or guest) session.

Login lives in a fixture rather than in the test body, so:
  * tests describe only the scenario under test,
  * a login problem shows up in Allure under "Set up", not as a scenario step,
  * new E2E tests get authentication for free by asking for `flow`.
"""
import allure
import pytest

from flows import ShoppingFlow


@pytest.fixture
def flow(page, config) -> ShoppingFlow:
    """A ShoppingFlow whose session is already authenticated (user or guest)."""
    shopping = ShoppingFlow(page, config)
    auth_mode = shopping.authenticate()
    allure.dynamic.parameter("auth_mode", auth_mode)
    return shopping
