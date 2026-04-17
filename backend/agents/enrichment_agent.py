"""
Enrichment Agent — enhances raw company records with buying signals and ICP scores.
LLM is used for qualitative description enrichment only; signal/ICP scoring is rule-based.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, List

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import (
    AgentResult, AgentStatus, CompanyRecord, EnrichedCompany, ExecutionPlan
)
from backend.tools.icp_scorer import ICPScorer
from backend.tools.signal_detector import SignalDetector

logger = logging.getLogger(__name__)

_ENRICHMENT_SYSTEM = """\
You are a B2B sales intelligence analyst. Given a list of company records, add enriched insight
for each company. Respond ONLY with a JSON array (one object per company) in this format:
[
  {
    "id": "<company id>",
    "enrichment_notes": "<1-2 sentences of actionable sales context>",
    "data_quality": <0.0-1.0 based on completeness of the provided data>
  },
  ...
]
No markdown, no explanation — just the JSON array.
"""


class EnrichmentAgent(BaseAgent):
    name = "enrichment"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._signal_detector = SignalDetector()
        self._icp_scorer = ICPScorer()

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        retrieval_output = context.get("retrieval_output", {})
        companies: List[CompanyRecord] = retrieval_output.get("companies", [])
        plan: ExecutionPlan = context.get("plan")
        criteria_dict = plan.target_criteria.model_dump() if plan else {}

        if not companies:
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                confidence=0.0,
                error="No companies to enrich",
            )

        await self._emit_start(f"Enriching {len(companies)} companies with signals and ICP scores")

        # Rule-based enrichment (no LLM needed)
        enriched_companies: List[EnrichedCompany] = []
        for company in companies:
            signals = self._signal_detector.detect(company)
            icp_score = self._icp_scorer.score(company, criteria_dict, signals)
            enriched_companies.append(EnrichedCompany(
                company=company,
                signals=signals,
                icp_score=icp_score,
                data_quality=self._data_quality(company),
            ))

        # LLM enrichment in batches of 3 (qualitative notes only)
        batch_size = 3
        llm_notes: Dict[str, str] = {}
        for i in range(0, len(enriched_companies), batch_size):
            batch = enriched_companies[i:i + batch_size]
            notes = await self._enrich_batch(batch, criteria_dict)
            llm_notes.update(notes)

        # Merge LLM notes back
        for ec in enriched_companies:
            ec.enrichment_notes = llm_notes.get(ec.company.id, ec.enrichment_notes)
            await self._emit_chunk(
                {
                    "company": ec.company.name,
                    "icp_score": ec.icp_score.composite,
                    "tier": ec.icp_score.tier.value,
                    "signal_count": len(ec.signals),
                },
                label="enriched_company"
            )

        # Filter out excluded companies (ICP < 0.20)
        qualified = [ec for ec in enriched_companies if ec.icp_score.composite >= 0.20]
        logger.info("Enrichment: %d/%d companies qualified (ICP >= 0.20)", len(qualified), len(enriched_companies))

        # Confidence = mean composite ICP score of qualified results
        if qualified:
            mean_icp = sum(ec.icp_score.composite for ec in qualified) / len(qualified)
        else:
            mean_icp = 0.1

        await self._emit_complete(mean_icp, f"Enriched {len(qualified)} qualified companies")

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            confidence=round(mean_icp, 3),
            output={"enriched_companies": qualified},
        )

    # ------------------------------------------------------------------
    # LLM batch enrichment
    # ------------------------------------------------------------------

    async def _enrich_batch(
        self, batch: List[EnrichedCompany], criteria_dict: Dict
    ) -> Dict[str, str]:
        if not batch:
            return {}

        companies_text = "\n".join(
            f"- id: {ec.company.id}, name: {ec.company.name}, "
            f"industry: {ec.company.industry}, size: {ec.company.company_size}, "
            f"stage: {ec.company.funding_stage.value}, "
            f"news: {ec.company.recent_news[:100] if ec.company.recent_news else 'N/A'}, "
            f"hiring: {', '.join(ec.company.hiring_roles[:3])}"
            for ec in batch
        )
        criteria_text = (
            f"Target: {criteria_dict.get('industry', 'any industry')}, "
            f"personas: {criteria_dict.get('personas', [])}"
        )
        user_prompt = f"Companies:\n{companies_text}\n\nContext: {criteria_text}"

        cache_key = self._cache.make_key(
            "enrichment",
            self._cache.hash_dict({
                "ids": [ec.company.id for ec in batch],
                "criteria": criteria_dict,
            })
        )
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        raw = await self._call_llm(
            system=_ENRICHMENT_SYSTEM,
            user=user_prompt,
            max_tokens=600,
            use_cache=False,
        )

        result: Dict[str, str] = {}
        try:
            text = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
            text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                items = json.loads(match.group(0))
                for item in items:
                    cid = item.get("id", "")
                    notes = item.get("enrichment_notes", "")
                    if cid:
                        result[cid] = notes
        except Exception as e:
            logger.warning("Enrichment batch LLM parse error: %s", e)

        self._cache.set(cache_key, result, ttl_seconds=300)
        return result

    @staticmethod
    def _data_quality(company: CompanyRecord) -> float:
        fields = [
            company.industry, company.geography, company.funding_stage,
            company.description, company.recent_news, company.growth_yoy,
        ]
        filled = sum(1 for f in fields if f and f != 0.0)
        return round(filled / len(fields), 2)
