"""Bound the optional SportsDB fallback, without adding jobs or provider calls.

This is a cooperative I/O budget, NOT a hard real-time deadline: DNS resolution,
JSON decoding and database persistence cannot be preempted here. A read already
in progress can overrun the deadline by at most its configured socket timeout
under normal urllib socket semantics. Other providers are intentionally unchanged.
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable


class SportsDBBudgetExhausted(TimeoutError):
    """Safe marker without URLs, credentials or provider content."""

    def __init__(self) -> None:
        super().__init__("SPORTSDB_TIME_BUDGET_EXHAUSTED")


class SportsDBResponseTooLarge(ValueError):
    def __init__(self) -> None:
        super().__init__("SPORTSDB_RESPONSE_SIZE_LIMIT")


@dataclass
class SportsDBFetchBudget:
    seconds: float = 8.0
    per_request_seconds: float = 4.0
    max_response_bytes: int = 4 * 1024 * 1024
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    requests_started: int = field(default=0, init=False)
    responses_completed: int = field(default=0, init=False)
    exhausted: bool = field(default=False, init=False)
    _started: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.seconds = float(self.seconds)
        self.per_request_seconds = float(self.per_request_seconds)
        if not math.isfinite(self.seconds) or self.seconds < 0:
            raise ValueError("seconds must be finite and nonnegative")
        if not math.isfinite(self.per_request_seconds) or self.per_request_seconds <= 0:
            raise ValueError("per_request_seconds must be finite and positive")
        if not isinstance(self.max_response_bytes, int) or self.max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be a positive integer")
        self._started = self.clock()

    def remaining(self) -> float:
        return max(0.0, self.seconds - max(0.0, self.clock() - self._started))

    def request_timeout(self) -> float:
        remaining = self.remaining()
        if remaining <= 0.05:
            self.exhausted = True
            raise SportsDBBudgetExhausted()
        return min(self.per_request_seconds, remaining)

    def read_json(self, request: urllib.request.Request, *, opener=None) -> Any:
        """Keep a per-response size limit and check the shared budget per chunk."""
        timeout = self.request_timeout()
        opener = opener or urllib.request.urlopen
        self.requests_started += 1
        with opener(request, timeout=timeout) as response:
            # HTTPResponse.read1 does at most one buffered/raw read. Tests may
            # supply a conventional stream exposing only read.
            read = getattr(response, "read1", None) or response.read
            chunks = []
            size = 0
            while True:
                self.request_timeout()
                chunk = read(min(65536, self.max_response_bytes + 1 - size))
                self.request_timeout()
                if not chunk:
                    break
                size += len(chunk)
                if size > self.max_response_bytes:
                    raise SportsDBResponseTooLarge()
                chunks.append(chunk)
            payload = json.loads(b"".join(chunks).decode("utf-8", errors="replace"))
            self.request_timeout()
        self.responses_completed += 1
        return payload

    def snapshot(self) -> dict[str, Any]:
        return {
            "scope": "SPORTSDB_FALLBACK_ONLY",
            "budget_seconds": self.seconds,
            "per_request_seconds": self.per_request_seconds,
            "elapsed_ms": max(0, round((self.clock() - self._started) * 1000)),
            "requests_started": self.requests_started,
            "responses_completed": self.responses_completed,
            "budget_exhausted": self.exhausted,
            "hard_deadline_guaranteed": False,
        }


def fallback_budget(cycle_started: float, *, clock=time.monotonic) -> SportsDBFetchBudget:
    """Reserve downstream time; do not start fallback after the soft cycle target.

No additional API requests are introduced. The 14 s soft target is not a
promise about the full cron, its other providers, DB work or Telegram delivery.
"""
    remaining = max(0.0, 14.0 - max(0.0, clock() - cycle_started))
    return SportsDBFetchBudget(seconds=min(8.0, remaining), clock=clock)
