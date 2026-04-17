import { useReducer, useCallback } from 'react'
import type { AgentEvent, AgentStepState, GTMResponse, QueryStatus } from '../types/gtm'
import { submitQuery } from '../api/client'

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const AGENT_ORDER = ['planner', 'retrieval', 'enrichment', 'critic', 'gtm_strategy']
const AGENT_LABELS: Record<string, string> = {
  planner: 'Planner',
  retrieval: 'Retrieval',
  enrichment: 'Enrichment',
  critic: 'Validator',
  gtm_strategy: 'GTM Strategy',
}

interface GTMQueryState {
  status: QueryStatus
  sessionId: string | null
  query: string
  agentSteps: AgentStepState[]
  finalResult: GTMResponse | null
  error: string | null
  overallConfidence: number
}

function initialSteps(): AgentStepState[] {
  return AGENT_ORDER.map((agent) => ({
    agent,
    label: AGENT_LABELS[agent] || agent,
    status: 'idle',
    retryCount: 0,
    chunks: [],
  }))
}

const initialState: GTMQueryState = {
  status: 'idle',
  sessionId: null,
  query: '',
  agentSteps: initialSteps(),
  finalResult: null,
  error: null,
  overallConfidence: 0,
}

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

type Action =
  | { type: 'SUBMIT'; query: string }
  | { type: 'SESSION_STARTED'; sessionId: string }
  | { type: 'SSE_EVENT'; event: AgentEvent }
  | { type: 'COMPLETE'; result: GTMResponse }
  | { type: 'ERROR'; error: string }
  | { type: 'RESET' }

function reducer(state: GTMQueryState, action: Action): GTMQueryState {
  switch (action.type) {
    case 'SUBMIT':
      return {
        ...initialState,
        status: 'submitting',
        query: action.query,
        agentSteps: initialSteps(),
      }

    case 'SESSION_STARTED':
      return { ...state, status: 'streaming', sessionId: action.sessionId }

    case 'SSE_EVENT': {
      const { event } = action
      const steps = [...state.agentSteps]
      const idx = steps.findIndex((s) => s.agent === event.agent)
      if (idx === -1) return handleOrchestratorEvent(state, event)

      const step = { ...steps[idx] }
      const payload = event.payload as Record<string, unknown>

      switch (event.event_type) {
        case 'AGENT_START':
          step.status = 'running'
          break
        case 'AGENT_COMPLETE':
          step.status = 'completed'
          step.confidence = payload.confidence as number
          step.summary = payload.summary as string
          break
        case 'AGENT_RETRY':
          step.status = 'retrying'
          step.retryCount = (step.retryCount || 0) + 1
          step.summary = `Retrying: ${payload.reason}`
          break
        case 'AGENT_ERROR':
          step.status = 'failed'
          step.summary = payload.error as string
          break
        case 'STREAM_CHUNK':
          step.chunks = [...step.chunks, payload]
          break
      }

      steps[idx] = step
      return { ...state, agentSteps: steps }
    }

    case 'COMPLETE':
      return {
        ...state,
        status: 'completed',
        finalResult: action.result,
        overallConfidence: action.result.confidence,
      }

    case 'ERROR':
      return { ...state, status: 'error', error: action.error }

    case 'RESET':
      return { ...initialState, agentSteps: initialSteps() }

    default:
      return state
  }
}

function handleOrchestratorEvent(state: GTMQueryState, event: AgentEvent): GTMQueryState {
  if (event.event_type === 'FINAL_OUTPUT') {
    const payload = event.payload as Record<string, unknown>
    const result = payload.result as GTMResponse
    return {
      ...state,
      status: 'completed',
      finalResult: result,
      overallConfidence: result?.confidence ?? state.overallConfidence,
    }
  }
  if (event.event_type === 'ERROR') {
    const payload = event.payload as Record<string, unknown>
    return { ...state, status: 'error', error: String(payload.error || 'Unknown error') }
  }
  return state
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useGTMQuery() {
  const [state, dispatch] = useReducer(reducer, initialState)

  const handleSSEEvent = useCallback((event: AgentEvent) => {
    dispatch({ type: 'SSE_EVENT', event })
    if (event.event_type === 'FINAL_OUTPUT') {
      const result = (event.payload as Record<string, unknown>).result as GTMResponse
      dispatch({ type: 'COMPLETE', result })
    }
    if (event.event_type === 'ERROR') {
      dispatch({ type: 'ERROR', error: String((event.payload as Record<string, unknown>).error) })
    }
  }, [])

  const submit = useCallback(async (query: string) => {
    dispatch({ type: 'SUBMIT', query })
    try {
      const { session_id } = await submitQuery(query)
      dispatch({ type: 'SESSION_STARTED', sessionId: session_id })
      return session_id
    } catch (err) {
      dispatch({ type: 'ERROR', error: String(err) })
      return null
    }
  }, [])

  const reset = useCallback(() => dispatch({ type: 'RESET' }), [])

  return { state, submit, handleSSEEvent, reset }
}
