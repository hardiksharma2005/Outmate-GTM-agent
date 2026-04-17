"""
Rule-based buying signal detector. No LLM calls — pure heuristic scoring.
"""
from __future__ import annotations
import re
from datetime import date, datetime
from typing import List

from backend.models.schemas import CompanyRecord, HiringVelocity, Signal, SignalType


_EXPANSION_KEYWORDS = re.compile(
    r"\b(expand|hire|launch|raise|series|fund|acqui|partner|grow|scale|open)\b",
    re.IGNORECASE,
)
_SALES_ROLE_KEYWORDS = re.compile(
    r"\b(sales|revenue|account exec|ae |business develop|bd |vp sales|head of sales|sdr|bdr)\b",
    re.IGNORECASE,
)


class SignalDetector:

    def detect(self, company: CompanyRecord) -> List[Signal]:
        signals: List[Signal] = []

        # 1. HIRING_EXPANSION — actively hiring at a fast pace
        if company.hiring_velocity in (HiringVelocity.HIGH, HiringVelocity.MEDIUM):
            signals.append(Signal(
                type=SignalType.HIRING_EXPANSION,
                label="Active Hiring",
                score_contribution=0.15 if company.hiring_velocity == HiringVelocity.MEDIUM else 0.25,
                evidence=f"Hiring velocity: {company.hiring_velocity.value} ({len(company.hiring_roles)} open roles)",
            ))

        # 2. RECENT_FUNDING — funded within the last 12 months (relative to 2026-04-16)
        if company.last_funding_date:
            try:
                funded = datetime.strptime(company.last_funding_date, "%Y-%m-%d").date()
                days_since = (date(2026, 4, 16) - funded).days
                if days_since <= 365:
                    signals.append(Signal(
                        type=SignalType.RECENT_FUNDING,
                        label="Recently Funded",
                        score_contribution=0.30,
                        evidence=f"Raised ${company.total_funding_usd:,} ({company.funding_stage.value}) on {company.last_funding_date}",
                    ))
            except ValueError:
                pass

        # 3. HIGH_GROWTH — strong YoY growth
        if company.growth_yoy >= 0.8:
            signals.append(Signal(
                type=SignalType.HIGH_GROWTH,
                label="High Growth",
                score_contribution=0.25,
                evidence=f"{int(company.growth_yoy * 100)}% YoY growth",
            ))
        elif company.growth_yoy >= 0.4:
            signals.append(Signal(
                type=SignalType.HIGH_GROWTH,
                label="Moderate Growth",
                score_contribution=0.12,
                evidence=f"{int(company.growth_yoy * 100)}% YoY growth",
            ))

        # 4. SERIES_SWEET_SPOT — Series A, B, or C (ideal GTM targets)
        from backend.models.schemas import FundingStage
        if company.funding_stage in (FundingStage.SERIES_A, FundingStage.SERIES_B, FundingStage.SERIES_C):
            signals.append(Signal(
                type=SignalType.SERIES_SWEET_SPOT,
                label="Series Sweet Spot",
                score_contribution=0.15,
                evidence=f"At {company.funding_stage.value} — prime buying window for new solutions",
            ))

        # 5. HIRING_SALES_ROLES — expanding GTM/revenue org
        sales_roles = [r for r in company.hiring_roles if _SALES_ROLE_KEYWORDS.search(r)]
        if sales_roles:
            signals.append(Signal(
                type=SignalType.HIRING_SALES_ROLES,
                label="Building Sales Team",
                score_contribution=0.20,
                evidence=f"Sales/revenue roles open: {', '.join(sales_roles[:3])}",
            ))

        # 6. COMPETITIVE_DISPLACEMENT — check if we can name a competitor being used
        if company.competitors:
            signals.append(Signal(
                type=SignalType.COMPETITIVE_DISPLACEMENT,
                label="Competitive Displacement Opportunity",
                score_contribution=0.10,
                evidence=f"Currently using or competing with: {', '.join(company.competitors[:3])}",
            ))

        # 7. Expansion keywords in recent news
        if company.recent_news and _EXPANSION_KEYWORDS.search(company.recent_news):
            # Only add if not already captured by RECENT_FUNDING
            if not any(s.type == SignalType.RECENT_FUNDING for s in signals):
                signals.append(Signal(
                    type=SignalType.HIRING_EXPANSION,
                    label="Expansion Signal in News",
                    score_contribution=0.08,
                    evidence=f"Recent news: {company.recent_news[:120]}",
                ))

        return signals

    def get_top_signals(self, signals: List[Signal], n: int = 3) -> List[Signal]:
        return sorted(signals, key=lambda s: s.score_contribution, reverse=True)[:n]
