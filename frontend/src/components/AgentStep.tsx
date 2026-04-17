import type { ReactNode } from 'react'
import type { AgentStepState } from '../types/gtm'
import { RetryBadge } from './RetryBadge'

const STATUS_ICONS: Record<string, string> = {
  idle: '○',
  running: '◌',
  completed: '✓',
  failed: '✗',
  retrying: '↺',
}

const STATUS_CLASS: Record<string, string> = {
  idle: 'step-idle',
  running: 'step-running',
  completed: 'step-completed',
  failed: 'step-failed',
  retrying: 'step-retrying',
}

interface AgentStepProps {
  step: AgentStepState
  index: number
}

export function AgentStep({ step }: AgentStepProps) {
  const icon = STATUS_ICONS[step.status] || '○'
  const cls = STATUS_CLASS[step.status] || 'step-idle'

  return (
    <div className={`agent-step ${cls}`}>
      <div className="step-icon">{step.status === 'running' ? <span className="pulse-dot" /> : icon}</div>
      <div className="step-body">
        <div className="step-header">
          <span className="step-name">{step.label}</span>
          {step.retryCount > 0 && (
            <RetryBadge count={step.retryCount} reason={step.summary} />
          )}
          {step.confidence !== undefined && step.status === 'completed' && (
            <span className="step-confidence" title="Agent confidence score">
              {Math.round(step.confidence * 100)}%
            </span>
          )}
        </div>
        {step.summary && (
          <div className="step-summary">{step.summary}</div>
        )}
        {step.status === 'running' && step.chunks.length > 0 && (
          <div className="step-chunks">
            {(step.chunks as Record<string, unknown>[]).slice(-3).map((chunk, i) => (
              <div key={i} className="chunk-item">
                {!!chunk.label && <span className="chunk-label">{String(chunk.label)}</span>}
                {renderChunkData((chunk.data ?? chunk) as Record<string, unknown>)}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function renderChunkData(data: Record<string, unknown>): ReactNode {
  if (!data) return null
  const d = data
  if (d.company) return <span>Enriched: {String(d.company)}</span>
  if (d.companies && Array.isArray(d.companies)) {
    return <span>Found: {(d.companies as string[]).join(', ')}</span>
  }
  if (d.hook) return <span>{String(d.hook)}</span>
  if (d.plan_summary) return <span>{String(d.plan_summary)}</span>
  return null
}
