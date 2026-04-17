"""
Retrieval Agent — converts the execution plan into data API filters and queries the mock data source.
Handles ambiguous queries, missing fields, and over-constrained filters.
"""
from __future__ import annotations
import hashlib
import json
import logging
from typing import Any, Dict, List, Tuple

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentResult, AgentStatus, CompanyRecord, ExecutionPlan
from backend.tools.mock_data_api import MockDataAPI

logger = logging.getLogger(__name__)

_MOCK_API = MockDataAPI()


class RetrievalAgent(BaseAgent):
    name = "retrieval"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        plan: ExecutionPlan = context.get("plan")
        if not plan:
            return AgentResult(
                agent_name=self.name, status=AgentStatus.FAILED,
                confidence=0.0, error="No execution plan in context"
            )

        correction_context = context.get("correction_context", {})
        avoid_filters = correction_context.get("avoid_filters", [])
        replace_filters = correction_context.get("replace_filters", {})

        await self._emit_start("Converting plan to data filters and querying company database")

        filters = self._resolve_filters(plan, avoid_filters, replace_filters)

        # Check LRU cache before hitting data source
        cache_key = self._cache.make_key("retrieval", self._filters_hash(filters))
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Retrieval cache hit for filters %s", filters)
            companies = cached
        else:
            companies = _MOCK_API.query_companies(filters)
            self._cache.set(cache_key, companies, ttl_seconds=120)

        broadened = False
        broadening_attempts = 0

        while len(companies) < 3 and broadening_attempts < 3:
            filters, removed = self._broaden_filters(filters, broadening_attempts)
            if removed:
                logger.info("Broadening filters: removed '%s' (got %d results)", removed, len(companies))
                companies = _MOCK_API.query_companies(filters)
                broadened = True
            broadening_attempts += 1

        # Stream companies in batches of 5
        for i in range(0, len(companies), 5):
            batch = companies[i:i + 5]
            await self._emit_chunk(
                {"companies": [c.name for c in batch], "count": len(batch)},
                label=f"batch_{i // 5 + 1}"
            )

        confidence = min(1.0, len(companies) / 10)
        if broadened:
            confidence = max(0.0, confidence - 0.10)

        await self._emit_complete(
            confidence,
            f"Retrieved {len(companies)} companies (broadened={broadened})"
        )

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            confidence=confidence,
            output={"companies": companies, "filters_used": filters, "broadened": broadened},
        )

    # ------------------------------------------------------------------
    # Filter resolution
    # ------------------------------------------------------------------

    def _resolve_filters(
        self,
        plan: ExecutionPlan,
        avoid_filters: List[str],
        replace_filters: Dict[str, str],
    ) -> Dict[str, Any]:
        criteria = plan.target_criteria
        filters: Dict[str, Any] = {}

        def should_include(key: str) -> bool:
            for af in avoid_filters:
                if af.startswith(key + ":") or af == key:
                    return False
            return True

        if criteria.industry and should_include("industry"):
            filters["industry"] = replace_filters.get("industry", criteria.industry)

        if criteria.geography and should_include("geography"):
            filters["geography"] = replace_filters.get("geography", criteria.geography)

        if criteria.funding_stage and should_include("funding_stage"):
            filters["funding_stage"] = replace_filters.get(
                "funding_stage", criteria.funding_stage
            )

        if criteria.company_size_min is not None:
            filters["company_size_min"] = criteria.company_size_min
        if criteria.company_size_max is not None:
            filters["company_size_max"] = criteria.company_size_max

        if criteria.tech_stack:
            filters["tech_stack"] = criteria.tech_stack[:3]  # top 3 to avoid over-constraint

        if criteria.hiring_roles and should_include("hiring_roles"):
            filters["hiring_roles"] = criteria.hiring_roles[:3]

        if criteria.growth_signal and should_include("growth_signal"):
            filters["growth_signal"] = replace_filters.get(
                "growth_signal", criteria.growth_signal
            )

        # Strip invalid filter keys injected by avoid_filters replacements
        for af in avoid_filters:
            key = af.split(":")[0]
            filters.pop(key, None)

        return filters

    def _broaden_filters(self, filters: Dict[str, Any], attempt: int) -> Tuple[Dict, str]:
        """Remove one filter per attempt to widen the result set."""
        # Priority of filters to remove (most restrictive first)
        removable = [
            "funding_stage",
            "company_size_min",
            "company_size_max",
            "tech_stack",
            "hiring_roles",
            "growth_signal",
            "geography",
            "industry",
        ]
        for key in removable:
            if key in filters:
                new_filters = {k: v for k, v in filters.items() if k != key}
                return new_filters, key
        return filters, ""

    @staticmethod
    def _filters_hash(filters: Dict[str, Any]) -> str:
        stable = json.dumps(filters, sort_keys=True, default=str)
        return hashlib.sha256(stable.encode()).hexdigest()[:16]
