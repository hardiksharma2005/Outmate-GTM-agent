import type { AgentStepState } from '../types/gtm'
import { AgentStep } from './AgentStep'

interface AgentTimelineProps {
  steps: AgentStepState[]
  retryCount?: number
}

export function AgentTimeline({ steps, retryCount = 0 }: AgentTimelineProps) {
  return (
    <div className="agent-timeline">
      <div className="timeline-header">
        <h3>Execution Timeline</h3>
        {retryCount > 0 && (
          <span className="retry-info">
            {retryCount} retry{retryCount > 1 ? 'ies' : ''} triggered
          </span>
        )}
      </div>
      <div className="timeline-steps">
        {steps.map((step, i) => (
          <div key={step.agent} className="timeline-step-wrapper">
            <AgentStep step={step} index={i} />
            {i < steps.length - 1 && (
              <div className={`timeline-connector ${step.status === 'completed' ? 'connector-active' : ''}`} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
