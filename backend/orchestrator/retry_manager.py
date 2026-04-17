"""
Retry Manager — tracks attempt state, injects corrections into context, enforces retry limits.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List

from backend.models.schemas import CriticVerdict

logger = logging.getLogger(__name__)


class RetryManager:
    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self.attempt = 0
        self.history: List[Dict[str, Any]] = []

    def can_retry(self) -> bool:
        return self.attempt < self.max_retries

    def prepare_retry(self, verdict: CriticVerdict, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mutate context to inject correction information for the next attempt.
        Clears stale outputs so agents re-execute with corrected inputs.
        """
        self.attempt += 1

        # Record this attempt in history
        self.history.append({
            "attempt": self.attempt,
            "issues": verdict.issues,
            "retry_reason": verdict.retry_reason,
            "hallucinated_filters": verdict.hallucinated_filters,
            "relevance_score": verdict.relevance_score,
        })

        # Build correction context from critic verdict
        correction_context = dict(verdict.corrections)
        correction_context["retry_reason"] = verdict.retry_reason
        correction_context["history_summary"] = self.get_history_summary()

        # Inject into context
        context["correction_context"] = correction_context
        context["_attempt"] = self.attempt

        # Clear stale outputs so agents re-run fresh
        context.pop("retrieval_output", None)
        context.pop("enrichment_output", None)

        # Only clear plan if a full re-plan is needed
        if self.requires_full_replan(verdict.issues):
            context.pop("plan", None)
            logger.info("Retry %d: full re-plan triggered", self.attempt)
        else:
            logger.info("Retry %d: re-retrieval only (plan preserved)", self.attempt)

        return context

    def requires_full_replan(self, issues: List[str]) -> bool:
        if len(issues) >= 3:
            return True
        if any("relevance" in i.lower() for i in issues):
            return True
        return False

    def get_history_summary(self) -> str:
        if not self.history:
            return "No previous attempts."
        lines = []
        for h in self.history:
            lines.append(
                f"Attempt {h['attempt']}: {h['retry_reason']} "
                f"(relevance={h['relevance_score']:.2f})"
            )
        return " | ".join(lines)
