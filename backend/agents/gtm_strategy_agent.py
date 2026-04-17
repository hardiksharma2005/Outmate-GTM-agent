"""
GTM Strategy Agent — generates personalized outreach hooks, angles, and email snippets.
Implements: Feature B (ICP Scoring) and Feature C (Multi-Persona Targeting).
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, List

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import (
    AgentResult, AgentStatus, EmailSnippet, EnrichedCompany,
    ExecutionPlan, GTMStrategy, PersonaPlay, Signal
)

logger = logging.getLogger(__name__)

_STRATEGY_SYSTEM = """\
You are an elite B2B GTM strategist and outbound copywriter. You specialize in creating
hyper-personalized, signal-based outreach for enterprise sales teams.

Given enriched company data and target personas, generate a complete GTM strategy.
Respond ONLY with valid JSON in this exact schema:

{
  "hooks": ["<opening hook 1>", "<hook 2>", "<hook 3>"],
  "angles": ["<strategic angle 1>", "<angle 2>", "<angle 3>"],
  "competitive_positioning": ["<positioning statement 1>", "<positioning 2>"],
  "icp_insights": ["<insight about why these companies fit>", ...],
  "email_snippets": [
    {
      "persona": "<job title>",
      "subject": "<email subject line>",
      "opening": "<1-2 sentence opening referencing a specific signal>",
      "value_prop": "<1 sentence value proposition>",
      "cta": "<clear call to action>"
    },
    ...
  ],
  "persona_plays": [
    {
      "persona": "<job title>",
      "pain_points": ["<pain 1>", "<pain 2>"],
      "value_angles": ["<angle 1>", "<angle 2>"],
      "objection_handles": ["<objection: response>", ...]
    },
    ...
  ]
}

Rules:
- hooks must reference SPECIFIC buying signals (funding, hiring, growth, tech)
- email_snippets must be personalized to the persona role and company signals
- Generate one email snippet and persona play per persona provided
- No generic filler — every sentence must be specific and evidence-based
- No markdown, no explanation — just JSON
"""


class GTMStrategyAgent(BaseAgent):
    name = "gtm_strategy"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        enrichment_output: Dict = context.get("enrichment_output", {})
        enriched_companies: List[EnrichedCompany] = enrichment_output.get("enriched_companies", [])
        plan: ExecutionPlan = context.get("plan")
        personas: List[str] = (plan.personas if plan else []) or ["VP Sales", "CEO"]

        if not enriched_companies:
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                confidence=0.0,
                error="No enriched companies available for strategy generation",
            )

        await self._emit_start(
            f"Generating GTM strategy for {len(enriched_companies)} companies, "
            f"{len(personas)} personas"
        )

        # Sort by ICP score descending for top companies in prompt
        top_companies = sorted(
            enriched_companies,
            key=lambda ec: ec.icp_score.composite,
            reverse=True
        )[:8]

        # Build the user prompt
        user_prompt = self._build_prompt(top_companies, personas, plan)

        # Call LLM
        cache_key = self._cache.make_key(
            "gtm_strategy",
            self._cache.hash_dict({
                "company_ids": sorted([ec.company.id for ec in top_companies]),
                "personas": sorted(personas),
            })
        )
        cached = self._cache.get(cache_key)
        if cached:
            strategy_dict = cached
        else:
            raw = await self._call_llm(
                system=_STRATEGY_SYSTEM,
                user=user_prompt,
                max_tokens=3000,
                use_cache=False,
            )
            strategy_dict, err = self._parse_json(raw)
            if err or not strategy_dict:
                logger.warning("GTM strategy parse failed: %s", err)
                strategy_dict = self._fallback_strategy(top_companies, personas)
            else:
                self._cache.set(cache_key, strategy_dict, ttl_seconds=600)

        strategy = self._build_strategy(strategy_dict, personas)

        # Stream hooks as they're built
        for hook in strategy.hooks:
            await self._emit_chunk({"hook": hook}, label="hook")
        for snippet in strategy.email_snippets:
            await self._emit_chunk(
                {"persona": snippet.persona, "subject": snippet.subject},
                label="email_snippet"
            )

        # Confidence: ratio of signals present × relevance proxy
        total_signals = sum(len(ec.signals) for ec in top_companies)
        signal_richness = min(1.0, total_signals / (len(top_companies) * 5 + 1))
        mean_icp = sum(ec.icp_score.composite for ec in top_companies) / len(top_companies)
        confidence = round(signal_richness * 0.5 + mean_icp * 0.5, 3)

        await self._emit_complete(confidence, f"Generated {len(strategy.hooks)} hooks, {len(strategy.email_snippets)} email snippets")

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            confidence=confidence,
            output={"strategy": strategy},
        )

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        companies: List[EnrichedCompany],
        personas: List[str],
        plan: ExecutionPlan,
    ) -> str:
        company_lines = []
        for ec in companies:
            top_signals = sorted(ec.signals, key=lambda s: s.score_contribution, reverse=True)[:3]
            signal_text = "; ".join(s.evidence for s in top_signals) if top_signals else "No strong signals"
            company_lines.append(
                f"- {ec.company.name} ({ec.company.industry}, {ec.company.geography}, "
                f"{ec.company.funding_stage.value}, {ec.company.company_size} employees, "
                f"ICP: {ec.icp_score.composite:.2f})\n"
                f"  Signals: {signal_text}\n"
                f"  News: {ec.company.recent_news[:120]}\n"
                f"  Competitors: {', '.join(ec.company.competitors[:3])}\n"
                f"  Hiring: {', '.join(ec.company.hiring_roles[:3])}"
            )

        strategy_text = plan.strategy if plan else ""
        return (
            f"Target Personas: {', '.join(personas)}\n"
            f"GTM Strategy: {strategy_text}\n\n"
            f"Top ICP-qualified companies:\n" + "\n".join(company_lines)
        )

    # ------------------------------------------------------------------
    # Parse / build
    # ------------------------------------------------------------------

    def _parse_json(self, raw: str):
        text = raw.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
        try:
            return json.loads(text), ""
        except json.JSONDecodeError as e:
            return {}, str(e)

    def _build_strategy(self, d: Dict, personas: List[str]) -> GTMStrategy:
        snippets = []
        for s in d.get("email_snippets", []):
            try:
                snippets.append(EmailSnippet(
                    persona=s.get("persona", ""),
                    subject=s.get("subject", ""),
                    opening=s.get("opening", ""),
                    value_prop=s.get("value_prop", ""),
                    cta=s.get("cta", ""),
                ))
            except Exception:
                pass

        plays = []
        for p in d.get("persona_plays", []):
            try:
                plays.append(PersonaPlay(
                    persona=p.get("persona", ""),
                    pain_points=p.get("pain_points", []),
                    value_angles=p.get("value_angles", []),
                    objection_handles=p.get("objection_handles", []),
                ))
            except Exception:
                pass

        return GTMStrategy(
            hooks=d.get("hooks", []),
            angles=d.get("angles", []),
            email_snippets=snippets,
            persona_plays=plays,
            icp_insights=d.get("icp_insights", []),
            competitive_positioning=d.get("competitive_positioning", []),
        )

    def _fallback_strategy(self, companies: List[EnrichedCompany], personas: List[str]) -> Dict:
        """Deterministic fallback if LLM fails."""
        top = companies[0] if companies else None
        name = top.company.name if top else "your target"
        stage = top.company.funding_stage.value if top else "growth stage"
        return {
            "hooks": [
                f"Noticed {name} recently reached {stage} — typically when teams face scaling challenges we help solve.",
                f"{name} is hiring {top.company.hiring_roles[0] if top and top.company.hiring_roles else 'GTM roles'} — signals active expansion.",
                "Companies at your growth stage typically see 3x ROI within 6 months using our platform.",
            ],
            "angles": [
                "Growth-stage efficiency: reduce operational overhead while scaling revenue",
                "Competitive differentiation: leverage AI-native workflows your competitors aren't using yet",
                "Time-to-revenue acceleration for newly funded teams",
            ],
            "competitive_positioning": [
                f"Unlike {top.company.competitors[0] if top and top.company.competitors else 'incumbent tools'}, we're built for high-growth companies.",
            ],
            "icp_insights": [
                f"{len(companies)} companies matched your ICP criteria with a mean composite score of "
                f"{sum(ec.icp_score.composite for ec in companies) / len(companies):.2f}"
            ],
            "email_snippets": [
                {
                    "persona": p,
                    "subject": f"Quick question about scaling at {name}",
                    "opening": f"Saw {name} just {stage.lower()} — congratulations on the milestone.",
                    "value_prop": "We help GTM teams at your stage close 30% more pipeline in the same headcount.",
                    "cta": "Worth a 15-minute conversation this week?",
                }
                for p in personas[:3]
            ],
            "persona_plays": [
                {
                    "persona": p,
                    "pain_points": ["Scaling revenue without proportionally scaling headcount", "Data silos slowing GTM velocity"],
                    "value_angles": ["ROI within 90 days", "Integrates with existing stack in under a week"],
                    "objection_handles": ["'We already have a solution': 'Most of our best customers said the same — what changed was the quality of signal they could act on.'"],
                }
                for p in personas[:3]
            ],
        }
