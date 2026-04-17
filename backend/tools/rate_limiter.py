"""
Token bucket rate limiter for Anthropic API calls.
"""
from __future__ import annotations
import asyncio
import logging
import time
from typing import Dict

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Async token bucket: capacity=60 tokens, refill 1 token/second.
    Call `await acquire()` before each LLM API request.
    """

    def __init__(self, capacity: int = 60, refill_rate: float = 1.0) -> None:
        self._capacity = capacity
        self._tokens = float(capacity)
        self._refill_rate = refill_rate  # tokens per second
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._total_calls = 0
        self._total_wait_ms = 0.0

    async def acquire(self, tokens: int = 1) -> None:
        async with self._lock:
            self._refill()
            while self._tokens < tokens:
                wait_time = (tokens - self._tokens) / self._refill_rate
                logger.debug("Rate limiter waiting %.2fs for %d token(s)", wait_time, tokens)
                self._total_wait_ms += wait_time * 1000
                await asyncio.sleep(wait_time)
                self._refill()
            self._tokens -= tokens
            self._total_calls += 1

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def get_stats(self) -> Dict:
        return {
            "total_calls": self._total_calls,
            "total_wait_ms": round(self._total_wait_ms, 1),
            "available_tokens": round(self._tokens, 1),
        }
