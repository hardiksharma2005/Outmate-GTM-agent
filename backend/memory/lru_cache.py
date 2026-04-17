"""
Namespaced LRU+TTL cache for deduplicating LLM and API calls.
"""
from __future__ import annotations
import hashlib
import json
import logging
import time
from typing import Any, Optional

from cachetools import TTLCache

logger = logging.getLogger(__name__)


class GTMLRUCache:
    """
    A simple namespace-aware TTL cache backed by cachetools.TTLCache.
    Default: 256 entries, 5-minute TTL.
    """

    DEFAULT_TTL_SECONDS = 300  # 5 minutes

    def __init__(self, maxsize: int = 256, default_ttl: int = DEFAULT_TTL_SECONDS) -> None:
        self._default_ttl = default_ttl
        # Use a large TTLCache; per-key TTL is approximated via timestamp metadata
        self._cache: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)
        self._maxsize = maxsize
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._cache[key]
            self._misses += 1
            return None
        self._hits += 1
        return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        if len(self._cache) >= self._maxsize:
            # Evict oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._cache[key] = (value, time.monotonic() + ttl)

    def invalidate_pattern(self, prefix: str) -> int:
        """Remove all keys with the given prefix. Returns number evicted."""
        keys_to_del = [k for k in self._cache if k.startswith(prefix)]
        for k in keys_to_del:
            del self._cache[k]
        if keys_to_del:
            logger.debug("Cache: evicted %d keys matching prefix '%s'", len(keys_to_del), prefix)
        return len(keys_to_del)

    @staticmethod
    def make_key(agent_name: str, input_hash: str) -> str:
        return f"{agent_name}:{input_hash}"

    @staticmethod
    def hash_dict(d: dict) -> str:
        stable = json.dumps(d, sort_keys=True, default=str)
        return hashlib.sha256(stable.encode()).hexdigest()[:16]

    def stats(self) -> dict:
        return {
            "entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(1, self._hits + self._misses), 3),
        }
