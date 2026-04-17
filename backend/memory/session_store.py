"""
In-memory session store. Maps session_id → SessionState + asyncio.Queue for SSE events.
"""
from __future__ import annotations
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.models.schemas import AgentResult, GTMResponse

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    session_id: str
    query: str
    status: str = "started"          # started | running | completed | failed
    created_at: float = field(default_factory=time.time)
    agent_results: List[AgentResult] = field(default_factory=list)
    final_result: Optional[GTMResponse] = None
    retry_count: int = 0
    error: Optional[str] = None


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}
        self._queues: Dict[str, asyncio.Queue] = {}

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, query: str, session_id: Optional[str] = None) -> str:
        sid = session_id or str(uuid.uuid4())
        self._sessions[sid] = SessionState(session_id=sid, query=query)
        self._queues[sid] = asyncio.Queue()
        logger.info("Created session %s", sid)
        return sid

    def get_session(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, **kwargs: Any) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

    def set_result(self, session_id: str, result: GTMResponse) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.final_result = result
            session.status = result.status

    def get_result(self, session_id: str) -> Optional[GTMResponse]:
        session = self._sessions.get(session_id)
        return session.final_result if session else None

    # ------------------------------------------------------------------
    # SSE queue
    # ------------------------------------------------------------------

    def get_queue(self, session_id: str) -> asyncio.Queue:
        return self._queues.get(session_id, asyncio.Queue())

    async def push_event(self, session_id: str, event: Any) -> None:
        q = self._queues.get(session_id)
        if q:
            await q.put(event)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_old_sessions(self, max_age_seconds: int = 3600) -> int:
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.created_at > max_age_seconds
        ]
        for sid in expired:
            self._sessions.pop(sid, None)
            self._queues.pop(sid, None)
        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))
        return len(expired)

    def list_sessions(self) -> List[str]:
        return list(self._sessions.keys())


# Global singleton (shared across requests in the same process)
session_store = SessionStore()
