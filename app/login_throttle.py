"""Brute-force protection for /auth/login.

Counts failed logins per (username, client IP). After LOGIN_MAX_ATTEMPTS
failures inside the window the pair is locked out until the window expires.

NOTE: state lives in this process's memory. That is fine for one uvicorn
worker; with several workers/containers each keeps its own counters, so put a
shared limiter (Redis, or your reverse proxy / WAF) in front for production.
"""
import threading
import time

from app.config import get_settings


class LoginThrottle:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: dict[tuple[str, str], list[float]] = {}

    def _recent(self, key: tuple[str, str], now: float) -> list[float]:
        window = get_settings().LOGIN_LOCKOUT_SECONDS
        recent = [t for t in self._failures.get(key, []) if now - t < window]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def retry_after(self, key: tuple[str, str]) -> int:
        """Seconds until the key may try again, or 0 if it is not locked."""
        s = get_settings()
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            if len(recent) >= s.LOGIN_MAX_ATTEMPTS:
                return max(1, int(s.LOGIN_LOCKOUT_SECONDS - (now - recent[0])) + 1)
            return 0

    def record_failure(self, key: tuple[str, str]) -> None:
        now = time.monotonic()
        with self._lock:
            self._recent(key, now)
            self._failures.setdefault(key, []).append(now)

    def reset(self, key: tuple[str, str]) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_throttle = LoginThrottle()
