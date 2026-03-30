"""
Quota / rate limiter utilities (RPM / TPM / RPD).

Design goals:
- Thread-safe: can be shared across ThreadPoolExecutor workers.
- Conservative: never intentionally exceeds configured limits.
- Self-contained: no external deps.

Notes:
- RPM and TPM are implemented as rolling windows (last 60 seconds).
- RPD is tracked as a simple counter; optional persistence is provided so resume runs don't double-spend.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Optional, Tuple
from collections import deque


def _now() -> float:
    return time.monotonic()


def _sleep_s(seconds: float) -> None:
    if seconds <= 0:
        return
    time.sleep(seconds)


@dataclass(frozen=True)
class QuotaConfig:
    # Requests per minute
    rpm: Optional[int] = None
    # Tokens per minute
    tpm: Optional[int] = None
    # Requests per day
    rpd: Optional[int] = None
    # Safety factor (<1.0) to stay below the hard limit (useful when server-side windows are strict)
    safety: float = 0.95


class RollingWindowLimiter:
    """
    Generic rolling-window limiter with a 60s window.
    Tracks a stream of events as (timestamp, amount).
    """

    def __init__(self, *, limit_per_minute: Optional[int], safety: float = 0.95) -> None:
        self._limit = None if limit_per_minute is None else max(int(limit_per_minute * safety), 1)
        self._events: Deque[Tuple[float, int]] = deque()
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        cutoff = now - 60.0
        while self._events and self._events[0][0] <= cutoff:
            self._events.popleft()

    def _sum(self) -> int:
        return sum(a for _, a in self._events)

    def acquire(self, amount: int = 1) -> None:
        if self._limit is None:
            return

        amt = max(int(amount), 1)
        while True:
            with self._lock:
                now = _now()
                self._prune(now)
                used = self._sum()
                if used + amt <= self._limit:
                    self._events.append((now, amt))
                    return

                # Need to wait until enough budget falls out of the 60s window.
                # Compute earliest time when this would be true by walking from oldest.
                # Conservative: wait until at least one event expires, then re-check.
                if not self._events:
                    # Should not happen, but avoid div by zero.
                    wait_s = 0.5
                else:
                    oldest_ts = self._events[0][0]
                    wait_s = max(0.0, (oldest_ts + 60.0) - now) + 0.01
            _sleep_s(wait_s)


class DailyCounter:
    """
    Simple RPD counter with optional persistence.
    Persistence format: JSON {"used": int, "updated_at": unix_ts}
    """

    def __init__(self, *, limit_per_day: Optional[int], persist_path: Optional[Path] = None) -> None:
        self._limit = None if limit_per_day is None else int(limit_per_day)
        self._used = 0
        self._persist_path = persist_path
        self._lock = threading.Lock()

        if self._persist_path is not None:
            try:
                if self._persist_path.exists():
                    data = json.loads(self._persist_path.read_text(encoding="utf-8"))
                    self._used = int(data.get("used", 0) or 0)
            except Exception:
                # Best-effort; don't fail the pipeline for a counter read.
                self._used = 0

    @property
    def used(self) -> int:
        with self._lock:
            return int(self._used)

    @property
    def limit(self) -> Optional[int]:
        return self._limit

    def remaining(self) -> Optional[int]:
        if self._limit is None:
            return None
        with self._lock:
            return max(0, self._limit - int(self._used))

    def _persist(self) -> None:
        if self._persist_path is None:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps({"used": int(self._used), "updated_at": int(time.time())}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def consume_or_raise(self, amount: int = 1) -> None:
        if self._limit is None:
            return
        amt = max(int(amount), 1)
        with self._lock:
            if self._used + amt > self._limit:
                raise RuntimeError(f"RPD limit exceeded: used={self._used} + {amt} > limit={self._limit}")
            self._used += amt
            self._persist()


class QuotaLimiter:
    """
    Combined limiter for RPM + TPM + RPD.
    Use:
      limiter.acquire_request(estimated_tokens=...)
      ... call API ...
      limiter.on_response(actual_tokens=...)  # optional; used for telemetry only
    """

    def __init__(
        self,
        *,
        name: str,
        cfg: QuotaConfig,
        rpd_persist_path: Optional[Path] = None,
    ) -> None:
        self.name = name
        self.cfg = cfg
        self._req_limiter = RollingWindowLimiter(limit_per_minute=cfg.rpm, safety=cfg.safety)
        self._tok_limiter = RollingWindowLimiter(limit_per_minute=cfg.tpm, safety=cfg.safety)
        self._day = DailyCounter(limit_per_day=cfg.rpd, persist_path=rpd_persist_path)
        self._stats_lock = threading.Lock()
        self._n_429 = 0
        self._last_tokens_est = 0

    def remaining_rpd(self) -> Optional[int]:
        return self._day.remaining()

    def acquire_request(self, *, estimated_tokens: int = 0, rpd_cost: int = 1) -> None:
        # RPD is a hard stop
        self._day.consume_or_raise(rpd_cost)
        # RPM & TPM are rolling-window throttles
        self._req_limiter.acquire(1)
        if estimated_tokens and estimated_tokens > 0:
            self._tok_limiter.acquire(int(estimated_tokens))
        with self._stats_lock:
            self._last_tokens_est = int(max(0, estimated_tokens))

    def note_429(self) -> None:
        with self._stats_lock:
            self._n_429 += 1

    def snapshot(self) -> dict:
        with self._stats_lock:
            return {
                "name": self.name,
                "rpm": self.cfg.rpm,
                "tpm": self.cfg.tpm,
                "rpd": self.cfg.rpd,
                "rpd_used": self._day.used,
                "rpd_remaining": self._day.remaining(),
                "recent_est_tokens": self._last_tokens_est,
                "n_429": self._n_429,
            }


def quota_from_env(prefix: str, *, default_rpm: Optional[int], default_tpm: Optional[int], default_rpd: Optional[int]) -> QuotaConfig:
    """
    Read quota config from env:
      {prefix}_RPM, {prefix}_TPM, {prefix}_RPD, {prefix}_SAFETY
    """
    def _env_int(name: str, default: Optional[int]) -> Optional[int]:
        raw = os.getenv(name, "").strip()
        if raw == "":
            return default
        try:
            return int(raw)
        except Exception:
            return default

    def _env_float(name: str, default: float) -> float:
        raw = os.getenv(name, "").strip()
        if raw == "":
            return default
        try:
            return float(raw)
        except Exception:
            return default

    rpm = _env_int(f"{prefix}_RPM", default_rpm)
    tpm = _env_int(f"{prefix}_TPM", default_tpm)
    rpd = _env_int(f"{prefix}_RPD", default_rpd)
    safety = _env_float(f"{prefix}_SAFETY", 0.95)
    safety = max(0.1, min(1.0, safety))
    return QuotaConfig(rpm=rpm, tpm=tpm, rpd=rpd, safety=safety)


