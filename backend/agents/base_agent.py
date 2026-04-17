"""
Abstract base class for all GTM agents.
Provides LLM calling, event emission, confidence calculation, and logging.
"""
from __future__ import annotations
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.memory.lru_cache import GTMLRUCache
from backend.memory.session_store import session_store
from backend.models.events import AgentEvent, EventType
from backend.models.schemas import AgentResult, AgentStatus
from backend.tools.llm_client import LLMClient
from backend.tools.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str = "base"

    def __init__(
        self,
        llm_client: LLMClient,
        cache: GTMLRUCache,
        rate_limiter: RateLimiter,
        session_id: str = "",
    ) -> None:
        self._llm = llm_client
        self._cache = cache
        self._rate_limiter = rate_limiter
        self._session_id = session_id
        self._log = logging.getLogger(f"agent.{self.name}")

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Run agent logic. Returns AgentResult with output and confidence."""

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        use_cache: bool = True,
    ) -> str:
        return await self._llm.call(
            system=system,
            user=user,
            max_tokens=max_tokens,
            use_cache=use_cache,
            agent_name=self.name,
        )

    # ------------------------------------------------------------------
    # Event emission
    # ------------------------------------------------------------------

    async def _emit(self, event_type: EventType, payload: Dict[str, Any]) -> None:
        event = AgentEvent(
            event_type=event_type,
            agent=self.name,
            payload=payload,
            session_id=self._session_id,
        )
        await session_store.push_event(self._session_id, event)

    async def _emit_start(self, message: str = "") -> None:
        await self._emit(EventType.AGENT_START, {"message": message or f"{self.name} starting"})

    async def _emit_complete(self, confidence: float, summary: str = "") -> None:
        await self._emit(EventType.AGENT_COMPLETE, {
            "confidence": confidence,
            "summary": summary,
        })

    async def _emit_chunk(self, data: Any, label: str = "") -> None:
        await self._emit(EventType.STREAM_CHUNK, {"data": data, "label": label})

    async def _emit_retry(self, attempt: int, reason: str) -> None:
        await self._emit(EventType.AGENT_RETRY, {"attempt": attempt, "reason": reason})

    async def _emit_error(self, error: str) -> None:
        await self._emit(EventType.AGENT_ERROR, {"error": error})

    # ------------------------------------------------------------------
    # Confidence helpers
    # ------------------------------------------------------------------

    def _completeness_confidence(self, obj: Dict, required_keys: List[str]) -> float:
        filled = sum(1 for k in required_keys if obj.get(k))
        return round(filled / max(len(required_keys), 1), 2)

    # ------------------------------------------------------------------
    # Execution wrapper — captures timing and errors
    # ------------------------------------------------------------------

    async def run(self, context: Dict[str, Any]) -> AgentResult:
        start_ms = int(time.time() * 1000)
        attempt = context.get("_attempt", 0)
        try:
            result = await self.execute(context)
            result.duration_ms = int(time.time() * 1000) - start_ms
            result.attempt = attempt
            self._log.info("Completed in %dms, confidence=%.2f", result.duration_ms, result.confidence)
            return result
        except Exception as exc:
            duration_ms = int(time.time() * 1000) - start_ms
            self._log.error("Failed after %dms: %s", duration_ms, exc, exc_info=True)
            await self._emit_error(str(exc))
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                confidence=0.0,
                error=str(exc),
                duration_ms=duration_ms,
                attempt=attempt,
            )
