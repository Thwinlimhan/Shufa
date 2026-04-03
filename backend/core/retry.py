from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 4.0,
) -> T:
    delay = initial_delay
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except Exception as exc:  # pragma: no cover - network failure paths
            last_error = exc
            if attempt >= attempts:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)
    if last_error is None:  # pragma: no cover
        raise RuntimeError("retry_async_failed_without_exception")
    raise last_error


def retry_sync(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 4.0,
) -> T:
    delay = initial_delay
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - network failure paths
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(delay)
            delay = min(delay * 2, max_delay)
    if last_error is None:  # pragma: no cover
        raise RuntimeError("retry_sync_failed_without_exception")
    raise last_error
