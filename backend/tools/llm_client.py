"""
Groq SDK wrapper with LRU deduplication and rate limiting.
"""
from __future__ import annotations
import hashlib
import logging
import os
from typing import AsyncGenerator, Optional

from groq import AsyncGroq

from backend.memory.lru_cache import GTMLRUCache
from backend.tools.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        rate_limiter: Optional[RateLimiter] = None,
        cache: Optional[GTMLRUCache] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self._model = model
        self._client = AsyncGroq(api_key=self._api_key)
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

        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        text = response.choices[0].message.content or ""
        self._total_input_tokens += response.usage.prompt_tokens
        self._total_output_tokens += response.usage.completion_tokens

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

        stream = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            stream=True,
        )

        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

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
        }

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]
