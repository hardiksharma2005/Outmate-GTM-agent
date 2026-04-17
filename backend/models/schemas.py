from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FundingStage(str, Enum):
    PRE_SEED = "Pre-Seed"
    SEED = "Seed"
    SERIES_A = "Series A"
    SERIES_B = "Series B"
    SERIES_C = "Series C"
    SERIES_D = "Series D"
    SERIES_E = "Series E"
    SERIES_F = "Series F"
    PE = "PE"
    PUBLIC = "Public"


class SizeBand(str, Enum):
    STARTUP = "startup"
    SMB = "smb"
    MID_MARKET = "mid-market"
    ENTERPRISE = "enterprise"


class HiringVelocity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ICPTier(str, Enum):
    HOT = "Tier 1 - Hot"
    WARM = "Tier 2 - Warm"
    NURTURE = "Tier 3 - Nurture"
    EXCLUDED = "Excluded"


# ---------------------------------------------------------------------------
# Request / Response envelope
# ---------------------------------------------------------------------------

class GTMQueryRequest(BaseModel):
    query: str = Field(..., min_length=5, description="Natural language GTM query")
    session_id: Optional[str] = None


class GTMQueryResponse(BaseModel):
    session_id: str
    status: str = "started"


# ---------------------------------------------------------------------------
# Execution Plan
# ---------------------------------------------------------------------------

class PlanStep(BaseModel):
    step_id: str
    agent: str
    task: str
    depends_on: List[str] = []


class TargetCriteria(BaseModel):
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    geography: Optional[str] = None
    company_size_min: Optional[int] = None
    company_size_max: Optional[int] = None
    funding_stage: Optional[str] = None
    tech_stack: List[str] = []
    hiring_roles: List[str] = []
    revenue_range: Optional[str] = None
    growth_signal: Optional[str] = None


class ExecutionPlan(BaseModel):
    entity_type: str = "company"
    tasks: List[str] = []
    steps: List[PlanStep] = []
    target_criteria: TargetCriteria = Field(default_factory=TargetCriteria)
    personas: List[str] = []
    buying_signals_requested: List[str] = []
    strategy: str = ""
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Company data
# ---------------------------------------------------------------------------

class KeyContact(BaseModel):
    name: str
    title: str
    linkedin: Optional[str] = None


class CompanyRecord(BaseModel):
    id: str
    name: str
    domain: str
    industry: str
    sub_industry: str = ""
    company_size: int
    size_band: SizeBand
    geography: str
    hq_city: str
    funding_stage: FundingStage
    total_funding_usd: int = 0
    last_funding_date: Optional[str] = None
    revenue_range: str = ""
    tech_stack: List[str] = []
    hiring_roles: List[str] = []
    hiring_velocity: HiringVelocity = HiringVelocity.NONE
    growth_yoy: float = 0.0
    recent_news: str = ""
    linkedin_url: str = ""
    description: str = ""
    icp_tags: List[str] = []
    competitors: List[str] = []
    key_contacts: List[KeyContact] = []


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class SignalType(str, Enum):
    HIRING_EXPANSION = "HIRING_EXPANSION"
    RECENT_FUNDING = "RECENT_FUNDING"
    HIGH_GROWTH = "HIGH_GROWTH"
    TECH_FIT = "TECH_FIT"
    SERIES_SWEET_SPOT = "SERIES_SWEET_SPOT"
    HIRING_SALES_ROLES = "HIRING_SALES_ROLES"
    COMPETITIVE_DISPLACEMENT = "COMPETITIVE_DISPLACEMENT"


class Signal(BaseModel):
    type: SignalType
    label: str
    score_contribution: float
    evidence: str


# ---------------------------------------------------------------------------
# ICP Score
# ---------------------------------------------------------------------------

class ICPScore(BaseModel):
    fit: float = 0.0
    intent: float = 0.0
    growth: float = 0.0
    composite: float = 0.0
    tier: ICPTier = ICPTier.EXCLUDED
    explanation: str = ""


# ---------------------------------------------------------------------------
# Enriched Company
# ---------------------------------------------------------------------------

class EnrichedCompany(BaseModel):
    company: CompanyRecord
    signals: List[Signal] = []
    icp_score: ICPScore = Field(default_factory=ICPScore)
    enrichment_notes: str = ""
    data_quality: float = 1.0  # 0-1, lower if missing fields


# ---------------------------------------------------------------------------
# Critic
# ---------------------------------------------------------------------------

class CriticVerdict(BaseModel):
    approved: bool
    issues: List[str] = []
    hallucinated_filters: List[str] = []
    retry_reason: str = ""
    relevance_score: float = 0.0
    corrections: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# GTM Strategy
# ---------------------------------------------------------------------------

class EmailSnippet(BaseModel):
    persona: str
    subject: str
    opening: str
    value_prop: str
    cta: str


class PersonaPlay(BaseModel):
    persona: str
    pain_points: List[str] = []
    value_angles: List[str] = []
    objection_handles: List[str] = []


class GTMStrategy(BaseModel):
    hooks: List[str] = []
    angles: List[str] = []
    email_snippets: List[EmailSnippet] = []
    persona_plays: List[PersonaPlay] = []
    icp_insights: List[str] = []
    competitive_positioning: List[str] = []


# ---------------------------------------------------------------------------
# Agent Result
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class AgentResult(BaseModel):
    agent_name: str
    status: AgentStatus = AgentStatus.PENDING
    confidence: float = 0.0
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: int = 0
    attempt: int = 0


# ---------------------------------------------------------------------------
# Reasoning Trace
# ---------------------------------------------------------------------------

class TraceStep(BaseModel):
    step: str
    summary: str
    confidence: float
    attempt: int = 0


# ---------------------------------------------------------------------------
# Final GTM Response
# ---------------------------------------------------------------------------

class GTMResponse(BaseModel):
    session_id: str
    query: str
    plan: Optional[ExecutionPlan] = None
    results: List[EnrichedCompany] = []
    signals: List[Signal] = []
    gtm_strategy: Optional[GTMStrategy] = None
    confidence: float = 0.0
    reasoning_trace: List[TraceStep] = []
    retry_count: int = 0
    status: str = "completed"
    error: Optional[str] = None
