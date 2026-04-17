from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    AGENT_START = "AGENT_START"
    AGENT_COMPLETE = "AGENT_COMPLETE"
    AGENT_RETRY = "AGENT_RETRY"
    AGENT_ERROR = "AGENT_ERROR"
    STREAM_CHUNK = "STREAM_CHUNK"
    PLAN_READY = "PLAN_READY"
    RESULTS_READY = "RESULTS_READY"
    FINAL_OUTPUT = "FINAL_OUTPUT"
    ERROR = "ERROR"
    HEARTBEAT = "HEARTBEAT"


@dataclass
class AgentEvent:
    event_type: EventType
    agent: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""

    def to_sse_string(self) -> str:
        data = {
            "event_type": self.event_type.value,
            "agent": self.agent,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }
        return f"data: {json.dumps(data)}\n\n"

    @staticmethod
    def heartbeat() -> str:
        return ": ping\n\n"
