import time
import threading
from typing import Dict, List
from fastapi import Request, HTTPException, status


class InMemoryRateLimiter:
    """
    Sliding-window in-memory rate limiter per IP and endpoint.
    Thread-safe and supports automated test resets.
    """
    def __init__(self, max_requests: int = 10, window_seconds: int = 60, enabled: bool = True):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.enabled = enabled
        self._history: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, force_check: bool = False) -> None:
        if not self.enabled and not force_check:
            return

        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            timestamps = self._history.get(key, [])
            # Filter timestamps within current window
            valid_timestamps = [t for t in timestamps if t > window_start]

            if len(valid_timestamps) >= self.max_requests:
                retry_after = int(self.window_seconds - (now - valid_timestamps[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many authentication attempts. Please try again later.",
                    headers={"Retry-After": str(max(1, retry_after))},
                )

            valid_timestamps.append(now)
            self._history[key] = valid_timestamps

    def reset(self) -> None:
        with self._lock:
            self._history.clear()


# Default limiter instances for auth endpoints (5 attempts per minute)
auth_rate_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)


def get_client_ip(request: Request) -> str:
    """Extract client IP handling reverse proxy headers safely."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in X-Forwarded-For is client origin
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
