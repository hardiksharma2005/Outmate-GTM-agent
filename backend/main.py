"""
FastAPI application entrypoint.
Provides:
  POST /api/query   → submit GTM query, get session_id
  GET  /api/stream/{session_id}  → SSE stream of agent events
  GET  /api/result/{session_id}  → final GTMResponse JSON
  GET  /api/health  → health check
"""
from __future__ import annotations
import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.memory.lru_cache import GTMLRUCache
from backend.memory.session_store import session_store
from backend.models.events import AgentEvent, EventType
from backend.models.schemas import GTMQueryRequest, GTMQueryResponse, GTMResponse
from backend.orchestrator.orchestrator import Orchestrator
from backend.tools.llm_client import LLMClient
from backend.tools.rate_limiter import RateLimiter

load_dotenv()
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared singletons (process-wide)
# ---------------------------------------------------------------------------
_shared_cache = GTMLRUCache(maxsize=256)
_shared_rate_limiter = RateLimiter(capacity=60, refill_rate=1.0)
_shared_llm = LLMClient(
    api_key=os.getenv("ANTHROPIC_API_KEY", ""),
    model=os.getenv("MODEL_NAME", "claude-sonnet-4-6"),
    rate_limiter=_shared_rate_limiter,
    cache=_shared_cache,
)


# ---------------------------------------------------------------------------
# Background cleanup task
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start periodic session cleanup
    cleanup_task = asyncio.create_task(_cleanup_sessions_periodically())
    yield
    cleanup_task.cancel()


async def _cleanup_sessions_periodically() -> None:
    while True:
        await asyncio.sleep(600)  # every 10 minutes
        n = session_store.cleanup_old_sessions(max_age_seconds=3600)
        if n:
            logger.info("Cleaned up %d expired sessions", n)


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GTM Intelligence API",
    description="Multi-agent GTM intelligence engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "sessions_active": len(session_store.list_sessions()),
        "llm_stats": _shared_llm.get_usage_stats(),
        "rate_limiter": _shared_rate_limiter.get_stats(),
    }


@app.post("/api/query", response_model=GTMQueryResponse)
async def submit_query(request: GTMQueryRequest) -> GTMQueryResponse:
    """
    Accept a GTM query. Creates a session, starts the orchestrator pipeline
    as a background task, and returns the session_id immediately.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    session_id = request.session_id or str(uuid.uuid4())
    session_store.create_session(query=request.query, session_id=session_id)

    orchestrator = Orchestrator(
        session_id=session_id,
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        llm_client=_shared_llm,
        cache=_shared_cache,
        rate_limiter=_shared_rate_limiter,
    )

    # Run the pipeline in background
    asyncio.create_task(orchestrator.run(request.query))

    logger.info("Started pipeline for session %s: %s", session_id, request.query[:80])
    return GTMQueryResponse(session_id=session_id, status="started")


@app.get("/api/stream/{session_id}")
async def stream_events(session_id: str):
    """
    SSE endpoint. Streams AgentEvent objects as they're emitted by agents.
    Sends a heartbeat every 15 seconds to keep the connection alive.
    Closes after FINAL_OUTPUT or ERROR event.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = session_store.get_queue(session_id)
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                if isinstance(event, AgentEvent):
                    yield event.to_sse_string()
                    if event.event_type in (EventType.FINAL_OUTPUT, EventType.ERROR):
                        break
                else:
                    yield f"data: {event}\n\n"
            except asyncio.TimeoutError:
                yield AgentEvent.heartbeat()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/result/{session_id}", response_model=GTMResponse)
async def get_result(session_id: str) -> GTMResponse:
    """
    Poll for the final GTMResponse. Returns 202 if still processing, 200 when done.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    result = session_store.get_result(session_id)
    if result is None:
        raise HTTPException(status_code=202, detail="Processing in progress")

    return result


@app.get("/api/sessions")
async def list_sessions():
    """Debug endpoint — list active sessions."""
    sessions = []
    for sid in session_store.list_sessions():
        s = session_store.get_session(sid)
        if s:
            sessions.append({
                "session_id": sid,
                "status": s.status,
                "query": s.query[:60],
                "retry_count": s.retry_count,
            })
    return {"sessions": sessions}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
