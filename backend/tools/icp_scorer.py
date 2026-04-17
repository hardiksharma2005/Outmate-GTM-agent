"""
ICP Scoring Engine — computes Fit, Intent, Growth, and Composite scores.
All logic is deterministic (no LLM calls).
"""
from __future__ import annotations
import re
from datetime import date, datetime
from typing import Dict, List, Optional

from backend.models.schemas import (
    CompanyRecord, FundingStage, HiringVelocity, ICPScore, ICPTier, Signal, SignalType
)


# Funding stage ordinal for adjacency scoring
_STAGE_ORDER: Dict[str, int] = {
    FundingStage.PRE_SEED.value: 0,
    FundingStage.SEED.value: 1,
    FundingStage.SERIES_A.value: 2,
    FundingStage.SERIES_B.value: 3,
    FundingStage.SERIES_C.value: 4,
    FundingStage.SERIES_D.value: 5,
    FundingStage.SERIES_E.value: 6,
    FundingStage.SERIES_F.value: 7,
    FundingStage.PE.value: 8,
    FundingStage.PUBLIC.value: 9,
}

_EXPANSION_KWORDS = re.compile(
    r"\b(expand|hire|launch|raise|grow|scale|open|acqui)\b", re.IGNORECASE
)


class ICPScorer:

    def score(
        self,
        company: CompanyRecord,
        criteria: Dict,
        signals: Optional[List[Signal]] = None,
    ) -> ICPScore:
        signals = signals or []
        fit = self._fit(company, criteria)
        intent = self._intent(company, signals)
        growth = self._growth(company, signals)
        composite = fit * 0.45 + intent * 0.35 + growth * 0.20
        composite = min(1.0, max(0.0, composite))
        tier = self._tier(composite)
        explanation = self._explain(fit, intent, growth, composite, company, criteria)
        return ICPScore(
            fit=round(fit, 3),
            intent=round(intent, 3),
            growth=round(growth, 3),
            composite=round(composite, 3),
            tier=tier,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Fit Score (0-1)
    # ------------------------------------------------------------------

    def _fit(self, company: CompanyRecord, criteria: Dict) -> float:
        score = 0.0

        # Industry match (30%)
        target_industry = criteria.get("industry", "")
        if target_industry:
            if self._fuzzy_match(company.industry, target_industry):
                score += 0.30
            elif self._fuzzy_match(company.sub_industry, target_industry):
                score += 0.18
        else:
            score += 0.15  # no constraint = partial credit

        # Size match (20%)
        size_min = criteria.get("company_size_min")
        size_max = criteria.get("company_size_max")
        if size_min or size_max:
            lo = size_min or 0
            hi = size_max or 1_000_000
            if lo <= company.company_size <= hi:
                score += 0.20
            else:
                dist = min(
                    abs(company.company_size - lo),
                    abs(company.company_size - hi),
                )
                score += max(0.0, 0.20 * (1 - dist / max(hi, 1000)))
        else:
            score += 0.10  # no constraint = partial credit

        # Tech overlap (25%)
        target_tech = criteria.get("tech_stack", [])
        if target_tech:
            overlap = len(
                set(t.lower() for t in company.tech_stack)
                & set(t.lower() for t in target_tech)
            )
            score += 0.25 * (overlap / len(target_tech))
        else:
            score += 0.12

        # Geography match (15%)
        target_geo = criteria.get("geography", "")
        if target_geo:
            if self._fuzzy_match(company.geography, target_geo):
                score += 0.15
            else:
                # Same broad region
                us_regions = {"us", "usa", "united states", "north america"}
                eu_regions = {"uk", "germany", "france", "netherlands", "europe"}
                if (
                    target_geo.lower() in us_regions and company.geography.lower() in us_regions
                ) or (
                    target_geo.lower() in eu_regions and company.geography.lower() in eu_regions
                ):
                    score += 0.08
        else:
            score += 0.08

        # Funding stage match (10%)
        target_stage = criteria.get("funding_stage", "")
        if target_stage:
            co_idx = _STAGE_ORDER.get(company.funding_stage.value, -1)
            tg_idx = _STAGE_ORDER.get(target_stage, -1)
            if co_idx >= 0 and tg_idx >= 0:
                diff = abs(co_idx - tg_idx)
                score += max(0.0, 0.10 * (1 - diff / 6))
        else:
            score += 0.05

        return min(1.0, score)

    # ------------------------------------------------------------------
    # Intent Score (0-1)
    # ------------------------------------------------------------------

    def _intent(self, company: CompanyRecord, signals: List[Signal]) -> float:
        score = 0.0

        # Hiring sales/revenue roles (+0.30)
        from backend.tools.signal_detector import _SALES_ROLE_KEYWORDS
        if any(_SALES_ROLE_KEYWORDS.search(r) for r in company.hiring_roles):
            score += 0.30

        # Funded within 6 months of 2026-04-16 (+0.25)
        if company.last_funding_date:
            try:
                funded = datetime.strptime(company.last_funding_date, "%Y-%m-%d").date()
                days_since = (date(2026, 4, 16) - funded).days
                if days_since <= 180:
                    score += 0.25
                elif days_since <= 365:
                    score += 0.12
            except ValueError:
                pass

        # High hiring velocity (+0.20)
        if company.hiring_velocity == HiringVelocity.HIGH:
            score += 0.20
        elif company.hiring_velocity == HiringVelocity.MEDIUM:
            score += 0.10

        # Expansion keywords in news (+0.15)
        if company.recent_news and _EXPANSION_KWORDS.search(company.recent_news):
            score += 0.15

        # High growth YoY (+0.10)
        if company.growth_yoy > 0.5:
            score += 0.10

        return min(1.0, score)

    # ------------------------------------------------------------------
    # Growth Score (0-1)
    # ------------------------------------------------------------------

    def _growth(self, company: CompanyRecord, signals: List[Signal]) -> float:
        base = min(1.0, company.growth_yoy)

        # Large companies grow slower — discount
        if company.company_size > 1000:
            base *= 0.7

        # Recent funding accelerates proxy (cap at 1.0)
        has_recent_funding = any(s.type == SignalType.RECENT_FUNDING for s in signals)
        if has_recent_funding:
            base *= 1.2

        return min(1.0, base)

    # ------------------------------------------------------------------
    # Tier & Explanation
    # ------------------------------------------------------------------

    @staticmethod
    def _tier(composite: float) -> ICPTier:
        if composite >= 0.75:
            return ICPTier.HOT
        if composite >= 0.55:
            return ICPTier.WARM
        if composite >= 0.35:
            return ICPTier.NURTURE
        return ICPTier.EXCLUDED

    @staticmethod
    def _explain(
        fit: float, intent: float, growth: float, composite: float,
        company: CompanyRecord, criteria: Dict
    ) -> str:
        parts = []
        if fit >= 0.7:
            parts.append(f"strong industry/size fit ({fit:.0%})")
        elif fit >= 0.4:
            parts.append(f"moderate fit ({fit:.0%})")
        else:
            parts.append(f"weak fit ({fit:.0%})")

        if intent >= 0.6:
            parts.append("high buying intent (active hiring + expansion signals)")
        elif intent >= 0.3:
            parts.append("some buying intent signals")

        if growth >= 0.7:
            parts.append(f"fast-growing ({int(company.growth_yoy*100)}% YoY)")

        return f"{company.name}: {'; '.join(parts)}. Composite ICP score: {composite:.2f}"

    @staticmethod
    def _fuzzy_match(field: str, query: str) -> bool:
        return query.lower() in field.lower() or field.lower() in query.lower()
