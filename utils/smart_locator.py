"""Multi-candidate locator: tries each selector in order and uses the first
one that is attached/visible. eBay ships several page layouts at once
(old `s-item` vs new `s-card` result cards, etc.), so a single selector breaks.
"""
from __future__ import annotations

import logging
from typing import Sequence

from playwright.sync_api import Locator, Page, TimeoutError as PwTimeout

from utils.errors import ElementNotFoundError

log = logging.getLogger(__name__)


class SmartLocator:
    def __init__(self, page: Page, name: str, candidates: Sequence[str]):
        self.page = page
        self.name = name
        self.candidates = list(candidates)

    def resolve(self, timeout_ms: int = 5000, state: str = "visible") -> Locator:
        per_try = max(timeout_ms // max(len(self.candidates), 1), 500)
        for selector in self.candidates:
            loc = self.page.locator(selector).first
            try:
                loc.wait_for(state=state, timeout=per_try)
                log.debug("[%s] matched %s", self.name, selector)
                return loc
            except PwTimeout:
                log.debug("[%s] no match for %s", self.name, selector)
        raise ElementNotFoundError(self.name, self.page.url, self.candidates, timeout_ms)

    def try_resolve(self, timeout_ms: int = 2000, state: str = "visible") -> Locator | None:
        try:
            return self.resolve(timeout_ms, state)
        except ElementNotFoundError:
            return None

    def all(self) -> Locator:
        """Locator for every element matched by the first selector that has hits."""
        for selector in self.candidates:
            loc = self.page.locator(selector)
            if loc.count() > 0:
                return loc
        return self.page.locator(self.candidates[0])
