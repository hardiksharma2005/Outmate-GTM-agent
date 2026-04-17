"""
Planner Agent — decomposes a natural-language GTM query into a structured ExecutionPlan.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, List, Tuple

from backend.agents.base_agent import BaseAgent
from backend.models.events import EventType
from backend.models.schemas import (
    AgentResult, AgentStatus, ExecutionPlan, PlanStep, TargetCriteria
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a GTM (Go-To-Market) Intelligence Planner. Your job is to analyze a sales/marketing query
and decompose it into a structured execution plan for a multi-agent system.

You MUST respond with ONLY valid JSON — no markdown, no explanation, no code fences.

Output this exact schema:
{
  "entity_type": "company",
  "tasks": ["search", "enrich", "analyze", "generate_outreach"],
  "target_criteria": {
    "industry": "<industry string or null>",
    "sub_industry": "<sub-industry or null>",
    "geography": "<country/region or null>",
    "company_size_min": <int or null>,
    "company_size_max": <int or null>,
    "funding_stage": "<Pre-Seed|Seed|Series A|Series B|Series C|Series D|PE|Public|null>",
    "tech_stack": ["<tech>", ...],
    "hiring_roles": ["<role keyword>", ...],
    "revenue_range": "<range string or null>",
    "growth_signal": "<high|medium|low|null>"
  },
  "personas": ["<target role>", ...],
  "buying_signals_requested": ["<signal type>", ...],
  "strategy": "<one-sentence description of the GTM approach>",
  "confidence": <0.0-1.0>
}

Rules:
- Only include fields you are confident about. Set unknown fields to null or [].
- funding_stage MUST be one of: Pre-Seed, Seed, Series A, Series B, Series C, Series D, PE, Public (or null)
- geography MUST be a country or region name (e.g. "US", "UK", "Europe") or null
- Do NOT invent field names not in the schema above
- personas should be job titles mentioned or implied (e.g. "VP Sales", "CTO", "CEO")
- buying_signals_requested should be from: HIRING_EXPANSION, RECENT_FUNDING, HIGH_GROWTH, TECH_FIT, SERIES_SWEET_SPOT, HIRING_SALES_ROLES, COMPETITIVE_DISPLACEMENT
"""

_RETRY_SYSTEM_PROMPT = """\
You are a GTM Intelligence Planner re-planning after a previous attempt failed validation.

{retry_context}

You MUST respond with ONLY valid JSON using the same schema as before. Apply the corrections listed above.
Do NOT repeat the mistakes from the previous attempt.
"""


class PlannerAgent(BaseAgent):
    name = "planner"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        query = context["query"]
        attempt = context.get("_attempt", 0)
        correction_context = context.get("correction_context", {})

        await self._emit_start(f"Decomposing query into execution plan (attempt {attempt + 1})")

        # Build system prompt (with retry context if applicable)
        if attempt > 0 and correction_context:
            retry_lines = [f"RETRY ATTEMPT {attempt}/3 — Previous plan failed validation."]
            if correction_context.get("retry_reason"):
                retry_lines.append(f"Failure reason: {correction_context['retry_reason']}")
            if correction_context.get("avoid_filters"):
                retry_lines.append(f"Do NOT use these filters: {correction_context['avoid_filters']}")
            if correction_context.get("replace_filters"):
                retry_lines.append(f"Replace filters as follows: {correction_context['replace_filters']}")
            if correction_context.get("retry_hint"):
                retry_lines.append(f"Hint: {correction_context['retry_hint']}")
            if correction_context.get("history_summary"):
                retry_lines.append(f"Previous attempts: {correction_context['history_summary']}")
            retry_ctx = "\n".join(retry_lines)
            system = _RETRY_SYSTEM_PROMPT.format(retry_context=retry_ctx)
        else:
            system = _SYSTEM_PROMPT

        raw = await self._call_llm(system=system, user=query, max_tokens=1024)

        # Parse JSON
        plan_dict, parse_error = self._parse_json(raw)

        if parse_error or not plan_dict:
            logger.warning("Failed to parse planner output: %s | raw: %s", parse_error, raw[:200])
            # Emit partial chunk so UI shows something
            await self._emit_chunk({"raw": raw[:300]}, label="parse_error")
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                confidence=0.1,
                error=f"JSON parse failed: {parse_error}",
            )

        # Validate and build plan
        plan, issues = self._build_plan(plan_dict, query)
        confidence = self._completeness_confidence(
            plan_dict.get("target_criteria", {}),
            ["industry", "geography", "funding_stage"],
        )
        # Boost confidence if personas and strategy are present
        if plan.personas:
            confidence = min(1.0, confidence + 0.15)
        if plan.strategy:
            confidence = min(1.0, confidence + 0.10)

        await self._emit(EventType.PLAN_READY, {
            "plan": plan.model_dump(),
            "issues": issues,
        })
        await self._emit_chunk({"plan_summary": plan.strategy, "personas": plan.personas}, label="plan_ready")
        await self._emit_complete(confidence, f"Plan ready: {len(plan.tasks)} tasks, {len(plan.personas)} personas")

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            confidence=confidence,
            output=plan,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_json(self, raw: str) -> Tuple[Dict, str]:
        text = raw.strip()
        # Strip markdown fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        # Find first JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
        try:
            return json.loads(text), ""
        except json.JSONDecodeError as e:
            return {}, str(e)

    def _build_plan(self, d: Dict, query: str) -> Tuple[ExecutionPlan, List[str]]:
        issues = []
        criteria_raw = d.get("target_criteria") or {}
        try:
            criteria = TargetCriteria(**{
                k: v for k, v in criteria_raw.items()
                if k in TargetCriteria.model_fields and v is not None
            })
        except Exception as e:
            criteria = TargetCriteria()
            issues.append(f"criteria parse error: {e}")

        tasks = d.get("tasks", ["search", "enrich", "analyze", "generate_outreach"])
        steps = [
            PlanStep(step_id=f"step_{i}", agent=t.split("_")[0], task=t, depends_on=[])
            for i, t in enumerate(tasks)
        ]

        plan = ExecutionPlan(
            entity_type=d.get("entity_type", "company"),
            tasks=tasks,
            steps=steps,
            target_criteria=criteria,
            personas=d.get("personas", []),
            buying_signals_requested=d.get("buying_signals_requested", []),
            strategy=d.get("strategy", ""),
            confidence=float(d.get("confidence", 0.5)),
        )

        if not plan.personas:
            issues.append("no personas extracted")
        if not plan.target_criteria.industry:
            issues.append("no industry identified")

        return plan, issues
