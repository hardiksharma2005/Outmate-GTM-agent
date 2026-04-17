"""
Central Orchestrator — manages the full multi-agent pipeline with retry loop.

Pipeline:
  Planner → Retrieval → Enrichment → Critic
                 ↑ (retry if critic rejects)
  → GTM Strategy → Assemble GTMResponse
"""
from __future__ import annotations
import logging
import time
from typing import Any, Dict, List, Optional

from backend.agents.critic_agent import CriticAgent
from backend.agents.enrichment_agent import EnrichmentAgent
from backend.agents.gtm_strategy_agent import GTMStrategyAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.retrieval_agent import RetrievalAgent
from backend.memory.lru_cache import GTMLRUCache
from backend.memory.session_store import session_store
from backend.models.events import AgentEvent, EventType
from backend.models.schemas import (
    AgentResult, AgentStatus, CriticVerdict, EnrichedCompany, ExecutionPlan,
    GTMResponse, GTMStrategy, Signal, TraceStep
)
from backend.orchestrator.retry_manager import RetryManager
from backend.tools.llm_client import LLMClient
from backend.tools.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        session_id: str,
        max_retries: int = 3,
        llm_client: Optional[LLMClient] = None,
        cache: Optional[GTMLRUCache] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        self._session_id = session_id
        self._cache = cache or GTMLRUCache()
        self._rate_limiter = rate_limiter or RateLimiter()
        self._llm = llm_client or LLMClient(cache=self._cache, rate_limiter=self._rate_limiter)
        self._retry_manager = RetryManager(max_retries=max_retries)

        # Instantiate all agents with shared resources
        agent_kwargs = dict(
            llm_client=self._llm,
            cache=self._cache,
            rate_limiter=self._rate_limiter,
            session_id=session_id,
        )
        self._planner = PlannerAgent(**agent_kwargs)
        self._retrieval = RetrievalAgent(**agent_kwargs)
        self._enrichment = EnrichmentAgent(**agent_kwargs)
        self._critic = CriticAgent(**agent_kwargs)
        self._gtm = GTMStrategyAgent(**agent_kwargs)

        self._agent_results: Dict[str, AgentResult] = {}
        self._trace: List[TraceStep] = []

    async def run(self, query: str) -> GTMResponse:
        logger.info("[%s] Orchestrator starting for query: %s", self._session_id, query[:80])
        session_store.update_session(self._session_id, status="running")

        context: Dict[str, Any] = {
            "query": query,
            "_attempt": 0,
        }

        best_enriched: List[EnrichedCompany] = []
        best_verdict: Optional[CriticVerdict] = None
        best_plan: Optional[ExecutionPlan] = None
        approved = False

        # ------------------------------------------------------------------
        # Main retry loop: Planner → Retrieval → Enrichment → Critic
        # ------------------------------------------------------------------
        for loop_iteration in range(self._retry_manager.max_retries + 1):
            context["_attempt"] = loop_iteration

            # Step 1: Plan (re-plan only if needed or first attempt)
            if "plan" not in context:
                plan_result = await self._planner.run(context)
                self._agent_results["planner"] = plan_result
                self._record_trace("planning", plan_result)

                if plan_result.status == AgentStatus.FAILED:
                    await self._emit_error("Planning failed", query)
                    return self._error_response(query, "Planning failed: " + (plan_result.error or ""))

                context["plan"] = plan_result.output
                best_plan = plan_result.output

            # Step 2: Retrieve
            retrieval_result = await self._retrieval.run(context)
            self._agent_results["retrieval"] = retrieval_result
            self._record_trace("retrieval", retrieval_result)

            if retrieval_result.status == AgentStatus.FAILED:
                logger.warning("Retrieval failed on attempt %d", loop_iteration)
                if not self._retry_manager.can_retry():
                    break
                context = self._retry_manager.prepare_retry(
                    CriticVerdict(
                        approved=False,
                        issues=["Retrieval failed"],
                        retry_reason="Retrieval agent failed",
                        corrections={"broaden_filters": True},
                    ),
                    context,
                )
                continue

            context["retrieval_output"] = retrieval_result.output

            # Step 3: Enrich
            enrichment_result = await self._enrichment.run(context)
            self._agent_results["enrichment"] = enrichment_result
            self._record_trace("enrichment", enrichment_result)

            if enrichment_result.status != AgentStatus.FAILED:
                enriched = enrichment_result.output.get("enriched_companies", [])
                if enriched:
                    best_enriched = enriched
                    best_plan = context.get("plan", best_plan)

            context["enrichment_output"] = enrichment_result.output or {}

            # Step 4: Critic validation
            critic_result = await self._critic.run(context)
            self._agent_results["critic"] = critic_result
            self._record_trace("validation", critic_result)

            verdict: CriticVerdict = critic_result.output.get("verdict", CriticVerdict(approved=False))
            best_verdict = verdict

            if verdict.approved:
                approved = True
                logger.info("Critic approved on iteration %d", loop_iteration)
                break

            # Critic rejected — check if we can retry
            if not self._retry_manager.can_retry():
                logger.warning("Max retries reached (%d), proceeding with best available results",
                               self._retry_manager.max_retries)
                break

            logger.info("Retry %d/%d: %s",
                        loop_iteration + 1, self._retry_manager.max_retries,
                        verdict.retry_reason)
            context = self._retry_manager.prepare_retry(verdict, context)
            # Invalidate retrieval cache so corrected filters hit data source fresh
            self._cache.invalidate_pattern("retrieval:")

        # ------------------------------------------------------------------
        # Step 5: GTM Strategy (runs on best available results)
        # ------------------------------------------------------------------
        if best_enriched:
            context["enrichment_output"] = {"enriched_companies": best_enriched}
            if best_plan:
                context["plan"] = best_plan

            gtm_result = await self._gtm.run(context)
            self._agent_results["gtm_strategy"] = gtm_result
            self._record_trace("gtm_strategy", gtm_result)
        else:
            gtm_result = AgentResult(
                agent_name="gtm_strategy",
                status=AgentStatus.FAILED,
                confidence=0.0,
                error="No qualified companies to generate strategy for",
            )

        # ------------------------------------------------------------------
        # Assemble final response
        # ------------------------------------------------------------------
        response = self._assemble_response(
            query=query,
            plan=best_plan,
            enriched=best_enriched,
            gtm_result=gtm_result,
            approved=approved,
        )

        # Store in session and emit terminal event
        session_store.set_result(self._session_id, response)
        await session_store.push_event(
            self._session_id,
            AgentEvent(
                event_type=EventType.FINAL_OUTPUT,
                agent="orchestrator",
                payload={"result": response.model_dump()},
                session_id=self._session_id,
            ),
        )

        logger.info("[%s] Pipeline complete: confidence=%.2f, retries=%d, companies=%d",
                    self._session_id, response.confidence,
                    self._retry_manager.attempt, len(best_enriched))
        return response

    # ------------------------------------------------------------------
    # Assembly helpers
    # ------------------------------------------------------------------

    def _assemble_response(
        self,
        query: str,
        plan: Optional[ExecutionPlan],
        enriched: List[EnrichedCompany],
        gtm_result: AgentResult,
        approved: bool,
    ) -> GTMResponse:
        # Collect all unique signals
        all_signals: List[Signal] = []
        seen = set()
        for ec in enriched:
            for sig in ec.signals:
                key = (sig.type, sig.label)
                if key not in seen:
                    all_signals.append(sig)
                    seen.add(key)

        strategy: Optional[GTMStrategy] = None
        if gtm_result.output:
            strategy = gtm_result.output.get("strategy")

        confidence = self._aggregate_confidence()
        if not approved:
            # Penalty for not reaching clean approval
            confidence = max(0.10, confidence - 0.10)

        return GTMResponse(
            session_id=self._session_id,
            query=query,
            plan=plan,
            results=enriched,
            signals=all_signals[:10],  # top 10 unique signals
            gtm_strategy=strategy,
            confidence=round(confidence, 3),
            reasoning_trace=self._trace,
            retry_count=self._retry_manager.attempt,
            status="completed" if enriched else "failed",
        )

    def _aggregate_confidence(self) -> float:
        weights = {
            "planner":     0.10,
            "retrieval":   0.20,
            "enrichment":  0.25,
            "critic":      0.30,
            "gtm_strategy": 0.15,
        }
        total = 0.0
        weight_used = 0.0
        for name, weight in weights.items():
            result = self._agent_results.get(name)
            if result:
                total += result.confidence * weight
                weight_used += weight

        if weight_used == 0:
            return 0.0

        raw = total / weight_used
        # Retry penalty
        retry_penalty = self._retry_manager.attempt * 0.05
        return max(0.0, min(1.0, raw - retry_penalty))

    def _record_trace(self, step: str, result: AgentResult) -> None:
        summary = ""
        if result.output and isinstance(result.output, dict):
            # Build a short non-verbose summary
            if step == "planning":
                plan = result.output
                if isinstance(plan, ExecutionPlan):
                    summary = f"Identified {len(plan.tasks)} tasks, target: {plan.target_criteria.industry or 'any industry'}"
            elif step == "retrieval":
                companies = result.output.get("companies", [])
                summary = f"Retrieved {len(companies)} companies"
            elif step == "enrichment":
                enriched = result.output.get("enriched_companies", [])
                summary = f"Enriched {len(enriched)} qualified companies"
            elif step == "validation":
                verdict = result.output.get("verdict")
                if verdict:
                    summary = f"{'Approved' if verdict.approved else 'Rejected'}: {verdict.retry_reason or 'OK'}"
            elif step == "gtm_strategy":
                strategy = result.output.get("strategy")
                if strategy and isinstance(strategy, GTMStrategy):
                    summary = f"Generated {len(strategy.hooks)} hooks, {len(strategy.email_snippets)} email snippets"
        elif isinstance(result.output, ExecutionPlan):
            summary = f"Plan: {result.output.strategy[:80]}" if result.output.strategy else "Plan created"

        if not summary:
            summary = f"{'Completed' if result.status == AgentStatus.COMPLETED else 'Failed'}"

        self._trace.append(TraceStep(
            step=step,
            summary=summary,
            confidence=result.confidence,
            attempt=result.attempt,
        ))

    def _error_response(self, query: str, error: str) -> GTMResponse:
        return GTMResponse(
            session_id=self._session_id,
            query=query,
            status="failed",
            error=error,
            confidence=0.0,
            reasoning_trace=self._trace,
        )

    async def _emit_error(self, message: str, query: str) -> None:
        await session_store.push_event(
            self._session_id,
            AgentEvent(
                event_type=EventType.ERROR,
                agent="orchestrator",
                payload={"error": message, "query": query},
                session_id=self._session_id,
            ),
        )
