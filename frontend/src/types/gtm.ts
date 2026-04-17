// TypeScript interfaces mirroring backend Pydantic schemas

export type EventType =
  | 'AGENT_START'
  | 'AGENT_COMPLETE'
  | 'AGENT_RETRY'
  | 'AGENT_ERROR'
  | 'STREAM_CHUNK'
  | 'PLAN_READY'
  | 'RESULTS_READY'
  | 'FINAL_OUTPUT'
  | 'ERROR'
  | 'HEARTBEAT'

export interface AgentEvent {
  event_type: EventType
  agent: string
  payload: Record<string, unknown>
  timestamp: number
  session_id: string
}

export type AgentStepStatus = 'idle' | 'running' | 'completed' | 'failed' | 'retrying'

export interface AgentStepState {
  agent: string
  label: string
  status: AgentStepStatus
  confidence?: number
  summary?: string
  retryCount: number
  duration_ms?: number
  chunks: unknown[]
}

export interface ICPScore {
  fit: number
  intent: number
  growth: number
  composite: number
  tier: string
  explanation: string
}

export interface Signal {
  type: string
  label: string
  score_contribution: number
  evidence: string
}

export interface CompanyRecord {
  id: string
  name: string
  domain: string
  industry: string
  sub_industry: string
  company_size: number
  size_band: string
  geography: string
  hq_city: string
  funding_stage: string
  total_funding_usd: number
  last_funding_date: string | null
  revenue_range: string
  tech_stack: string[]
  hiring_roles: string[]
  hiring_velocity: string
  growth_yoy: number
  recent_news: string
  description: string
  icp_tags: string[]
  competitors: string[]
  key_contacts: { name: string; title: string; linkedin?: string }[]
}

export interface EnrichedCompany {
  company: CompanyRecord
  signals: Signal[]
  icp_score: ICPScore
  enrichment_notes: string
  data_quality: number
}

export interface EmailSnippet {
  persona: string
  subject: string
  opening: string
  value_prop: string
  cta: string
}

export interface PersonaPlay {
  persona: string
  pain_points: string[]
  value_angles: string[]
  objection_handles: string[]
}

export interface GTMStrategy {
  hooks: string[]
  angles: string[]
  email_snippets: EmailSnippet[]
  persona_plays: PersonaPlay[]
  icp_insights: string[]
  competitive_positioning: string[]
}

export interface PlanStep {
  step_id: string
  agent: string
  task: string
  depends_on: string[]
}

export interface TargetCriteria {
  industry?: string
  geography?: string
  funding_stage?: string
  company_size_min?: number
  company_size_max?: number
  tech_stack?: string[]
  hiring_roles?: string[]
}

export interface ExecutionPlan {
  entity_type: string
  tasks: string[]
  steps: PlanStep[]
  target_criteria: TargetCriteria
  personas: string[]
  buying_signals_requested: string[]
  strategy: string
  confidence: number
}

export interface TraceStep {
  step: string
  summary: string
  confidence: number
  attempt: number
}

export interface GTMResponse {
  session_id: string
  query: string
  plan?: ExecutionPlan
  results: EnrichedCompany[]
  signals: Signal[]
  gtm_strategy?: GTMStrategy
  confidence: number
  reasoning_trace: TraceStep[]
  retry_count: number
  status: string
  error?: string
}

export type QueryStatus = 'idle' | 'submitting' | 'streaming' | 'completed' | 'error'
