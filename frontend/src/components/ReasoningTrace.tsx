import type { TraceStep } from '../types/gtm'

interface ReasoningTraceProps {
  trace: TraceStep[]
}

export function ReasoningTrace({ trace }: ReasoningTraceProps) {
  if (!trace || trace.length === 0) return null

  return (
    <div className="reasoning-trace">
      <h4>Reasoning Trace</h4>
      <div className="trace-steps">
        {trace.map((step, i) => (
          <div key={i} className="trace-step">
            <div className="trace-step-header">
              <span className="trace-step-name">{step.step}</span>
              {step.attempt > 0 && (
                <span className="trace-retry-badge">retry {step.attempt}</span>
              )}
              <span className="trace-confidence">
                {Math.round(step.confidence * 100)}%
              </span>
            </div>
            <div className="trace-summary">{step.summary}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
