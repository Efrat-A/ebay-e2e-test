from __future__ import annotations

import functools
import logging
import time
from typing import Callable, Tuple, Type

log = logging.getLogger(__name__)


def retry(attempts: int = 3, delay_sec: float = 1.0,
          exceptions: Tuple[Type[BaseException], ...] = (Exception,)) -> Callable:
    """Retry a flaky UI step a few times before failing."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    if attempt == attempts:
                        raise
                    log.warning("%s failed (%s/%s): %s - retrying",
                                fn.__name__, attempt, attempts, exc)
                    time.sleep(delay_sec)
        return wrapper
    return decorator
