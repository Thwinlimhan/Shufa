from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_LOCK = Lock()


def _check_limit(key: str, limit: int, window_seconds: int) -> None:
    now = time.time()
    cutoff = now - window_seconds
    with _LOCK:
        bucket = _WINDOWS[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"rate_limit_exceeded:{limit}/{window_seconds}s",
            )
        bucket.append(now)


def enforce_rate_limit(request: Request, bucket: str, limit: int, window_seconds: int = 60) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = f"{bucket}:{client_ip}"
    _check_limit(key, limit=limit, window_seconds=window_seconds)
