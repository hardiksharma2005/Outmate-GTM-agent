"""
Critic / Validation Agent — evaluates pipeline outputs for relevance and hallucinations.
This is the gatekeeper that triggers the retry loop.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, List, Tuple

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import (
    AgentResult, AgentStatus, CriticVerdict, EnrichedCompany, ExecutionPlan
)
from backend.tools.mock_data_api import SCHEMA as DATA_SCHEMA

logger = logging.getLogger(__name__)

_RELEVANCE_SYSTEM = """\
You are a strict GTM data quality evaluator. Your job is to judge whether a set of company results
actually matches the original user query intent.

Rate the overall relevance on a scale from 0.0 to 1.0 where:
- 1.0 = All results are highly relevant to the query
- 0.7 = Most results are relevant with minor mismatches
- 0.4 = Only some results match; significant mismatch
- 0.1 = Results are mostly irrelevant

Respond with ONLY a JSON object:
{"relevance_score": <float>, "reasoning": "<one sentence>"}
No markdown, no explanation.
"""


class CriticAgent(BaseAgent):
    name = "critic"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        query: str = context.get("query", "")
        plan: ExecutionPlan = context.get("plan")
        enrichment_output: Dict = context.get("enrichment_output", {})
        enriched_companies: List[EnrichedCompany] = enrichment_output.get("enriched_companies", [])
        retrieval_output: Dict = context.get("retrieval_output", {})
        filters_used: Dict = retrieval_output.get("filters_used", {})
        attempt: int = context.get("_attempt", 0)

        await self._emit_start(f"Validating {len(enriched_companies)} results (attempt {attempt + 1})")

        issues: List[str] = []
        hallucinated_filters: List[str] = []

        # ------------------------------------------------------------------
        # Check 1: Hallucinated filters
        # ------------------------------------------------------------------
        hallucinated_filters = self._check_filter_hallucination(filters_used)
        if hallucinated_filters:
            issues.append(f"Hallucinated filters detected: {hallucinated_filters}")

        # ------------------------------------------------------------------
        # Check 2: Insufficient results
        # ------------------------------------------------------------------
        if len(enriched_companies) < 2:
            issues.append(f"Too few results: {len(enriched_companies)} (need at least 2)")

        # ------------------------------------------------------------------
        # Check 3: ICP quality threshold
        # ------------------------------------------------------------------
        if enriched_companies:
            mean_icp = sum(ec.icp_score.composite for ec in enriched_companies) / len(enriched_companies)
            if mean_icp < 0.30:
                issues.append(f"Low mean ICP score: {mean_icp:.2f} (threshold: 0.30)")
        else:
            mean_icp = 0.0

        # ------------------------------------------------------------------
        # Check 4: Relevance via LLM
        # ------------------------------------------------------------------
        relevance_score = await self._check_relevance(query, enriched_companies[:5])
        if relevance_score < 0.4:
            issues.append(f"Low relevance score: {relevance_score:.2f} (threshold: 0.40)")

        # ------------------------------------------------------------------
        # Build verdict
        # ------------------------------------------------------------------
        approved = len(issues) == 0
        corrections = self._build_corrections(issues, hallucinated_filters, filters_used, plan)

        retry_reason = "; ".join(issues) if issues else ""

        verdict = CriticVerdict(
            approved=approved,
            issues=issues,
            hallucinated_filters=hallucinated_filters,
            retry_reason=retry_reason,
            relevance_score=relevance_score,
            corrections=corrections,
        )

        confidence = 1.0 if approved else max(0.1, 0.5 - len(issues) * 0.1)

        if not approved:
            await self._emit_retry(attempt, retry_reason)
            logger.warning("Critic REJECTED (attempt %d): %s", attempt, retry_reason)
        else:
            logger.info("Critic APPROVED: relevance=%.2f, mean_icp=%.2f", relevance_score, mean_icp)

        await self._emit_complete(confidence, f"{'APPROVED' if approved else 'REJECTED'}: {len(issues)} issues")

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            confidence=confidence,
            output={"verdict": verdict, "relevance_score": relevance_score, "mean_icp": mean_icp},
        )

    # ------------------------------------------------------------------
    # Hallucination detection
    # ------------------------------------------------------------------

    def _check_filter_hallucination(self, filters_used: Dict) -> List[str]:
        known_fields = set(DATA_SCHEMA["fields"].keys())
        invalid_fields = set(DATA_SCHEMA.get("invalid_fields", []))
        hallucinated = []

        for key, value in filters_used.items():
            # Check field name validity
            if key in invalid_fields:
                hallucinated.append(f"{key} (invalid field name)")
                continue
            if key not in known_fields:
                hallucinated.append(f"{key} (unknown field)")
                continue

            # Check value validity for enum fields
            field_schema = DATA_SCHEMA["fields"].get(key, {})
            valid_values = field_schema.get("valid_values", [])
            if valid_values and not field_schema.get("fuzzy_match", False):
                if isinstance(value, str) and value not in valid_values:
                    hallucinated.append(f"{key}:{value} (invalid value, valid: {valid_values})")

        return hallucinated

    # ------------------------------------------------------------------
    # LLM relevance check
    # ------------------------------------------------------------------

    async def _check_relevance(
        self, query: str, companies: List[EnrichedCompany]
    ) -> float:
        if not companies:
            return 0.0

        company_summaries = "\n".join(
            f"- {ec.company.name} ({ec.company.industry}, {ec.company.geography}, "
            f"{ec.company.funding_stage.value}, {ec.company.company_size} employees)"
            for ec in companies
        )
        user_prompt = (
            f"Original query: {query}\n\n"
            f"Results:\n{company_summaries}"
        )

        cache_key = self._cache.make_key(
            "critic_relevance",
            self._cache.hash_dict({"query": query, "company_ids": [ec.company.id for ec in companies]})
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return float(cached)

        try:
            raw = await self._call_llm(
                system=_RELEVANCE_SYSTEM,
                user=user_prompt,
                max_tokens=100,
                use_cache=False,
            )
            text = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
            text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                score = float(parsed.get("relevance_score", 0.5))
                score = max(0.0, min(1.0, score))
                self._cache.set(cache_key, score, ttl_seconds=300)
                return score
        except Exception as e:
            logger.warning("Relevance LLM call failed: %s", e)

        return 0.5  # default if LLM fails

    # ------------------------------------------------------------------
    # Build corrections for RetryManager
    # ------------------------------------------------------------------

    def _build_corrections(
        self,
        issues: List[str],
        hallucinated_filters: List[str],
        filters_used: Dict,
        plan: ExecutionPlan,
    ) -> Dict[str, Any]:
        corrections: Dict[str, Any] = {}

        if hallucinated_filters:
            avoid = []
            replace = {}
            for hf in hallucinated_filters:
                key = hf.split(":")[0].split(" ")[0]
                avoid.append(key)
                # Suggest replacements for known bad values
                if "funding_stage" in hf and "IPO" in hf:
                    replace["funding_stage"] = "Public"
                elif "funding_stage" in hf and "Series" in hf:
                    pass  # will strip the filter
            corrections["avoid_filters"] = avoid
            corrections["replace_filters"] = replace
            corrections["retry_hint"] = (
                f"Filters {hallucinated_filters} are invalid. "
                "Use only: industry, geography, funding_stage (Pre-Seed/Seed/Series A-D/PE/Public), "
                "company_size_min/max, tech_stack, hiring_roles, growth_signal, size_band."
            )

        if any("Too few results" in i for i in issues):
            corrections["broaden_filters"] = True
            corrections["retry_hint"] = corrections.get("retry_hint", "") + \
                " Broaden your criteria — fewer constraints will yield more results."

        if any("Low relevance" in i for i in issues):
            corrections["retry_hint"] = corrections.get("retry_hint", "") + \
                " Results don't match query intent. Re-check industry and persona mapping."

        corrections["retry_reason"] = "; ".join(issues)
        return corrections

    # ------------------------------------------------------------------
    # Heuristic: does this require a full re-plan?
    # ------------------------------------------------------------------

    @staticmethod
    def requires_full_replan(issues: List[str]) -> bool:
        if len(issues) >= 3:
            return True
        if any("relevance" in i.lower() for i in issues):
            return True
        return False
