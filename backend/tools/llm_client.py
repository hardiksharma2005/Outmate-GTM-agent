"""
Anthropic SDK wrapper with LRU deduplication, rate limiting, and streaming.
"""
from __future__ import annotations
import hashlib
import json
import logging
import os
from typing import AsyncGenerator, Optional

import anthropic

from backend.memory.lru_cache import GTMLRUCache
from backend.tools.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-6",
        rate_limiter: Optional[RateLimiter] = None,
        cache: Optional[GTMLRUCache] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        self._rate_limiter = rate_limiter or RateLimiter()
        self._cache = cache or GTMLRUCache()
        self._cache_hits = 0
        self._total_calls = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    async def call(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        use_cache: bool = True,
        agent_name: str = "agent",
    ) -> str:
        cache_key = self._cache.make_key(agent_name, self._hash(system + user))

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._cache_hits += 1
                logger.debug("[%s] Cache hit for key %s", agent_name, cache_key)
                return cached

        await self._rate_limiter.acquire()
        self._total_calls += 1

        logger.info("[%s] LLM call #%d (model=%s, max_tokens=%d)",
                    agent_name, self._total_calls, self._model, max_tokens)

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )

        text = response.content[0].text if response.content else ""
        self._total_input_tokens += response.usage.input_tokens
        self._total_output_tokens += response.usage.output_tokens

        if use_cache:
            self._cache.set(cache_key, text)

        return text

    async def stream_call(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        agent_name: str = "agent",
    ) -> AsyncGenerator[str, None]:
        await self._rate_limiter.acquire()
        self._total_calls += 1

        async with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def get_usage_stats(self) -> dict:
        hit_rate = (
            round(self._cache_hits / max(1, self._total_calls + self._cache_hits), 3)
        )
        return {
            "total_llm_calls": self._total_calls,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": hit_rate,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "estimated_cost_usd": round(
                (self._total_input_tokens * 3.0 + self._total_output_tokens * 15.0) / 1_000_000, 4
            ),
        }

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]
