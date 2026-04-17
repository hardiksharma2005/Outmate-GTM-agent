import { useGTMQuery } from './hooks/useGTMQuery'
import { useSSE } from './hooks/useSSE'
import { QueryInput } from './components/QueryInput'
import { AgentTimeline } from './components/AgentTimeline'
import { ConfidenceMeter } from './components/ConfidenceMeter'
import { ResultCard } from './components/ResultCard'
import { GTMStrategyPanel } from './components/GTMStrategyPanel'
import { ReasoningTrace } from './components/ReasoningTrace'

export default function App() {
  const { state, submit, handleSSEEvent, reset } = useGTMQuery()
  const { status, sessionId, agentSteps, finalResult, error, overallConfidence } = state

  const isActive = status === 'streaming' || status === 'submitting'

  useSSE(sessionId, {
    onEvent: handleSSEEvent,
    onError: () => {},
    onClose: () => {},
  })

  const results = finalResult?.results ?? []
  const sortedResults = [...results].sort(
    (a, b) => b.icp_score.composite - a.icp_score.composite
  )

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon">⚡</span>
            <span className="logo-text">OutMate</span>
            <span className="logo-sub">GTM Intelligence Engine</span>
          </div>
          {status !== 'idle' && (
            <div className="header-confidence">
              <ConfidenceMeter value={overallConfidence} size={100} />
            </div>
          )}
        </div>
      </header>

      <main className="app-main">
        <QueryInput
          onSubmit={submit}
          disabled={isActive}
          onReset={status !== 'idle' ? reset : undefined}
          isStreaming={isActive}
        />

        {error && (
          <div className="error-banner">
            <strong>Error:</strong> {error}
          </div>
        )}

        {status !== 'idle' && (
          <div className="pipeline-view">
            <div className="left-panel">
              <AgentTimeline
                steps={agentSteps}
                retryCount={finalResult?.retry_count ?? 0}
              />
              {finalResult?.reasoning_trace && (
                <ReasoningTrace trace={finalResult.reasoning_trace} />
              )}
            </div>

            <div className="right-panel">
              {finalResult?.gtm_strategy && (
                <GTMStrategyPanel strategy={finalResult.gtm_strategy} />
              )}

              {sortedResults.length > 0 && (
                <div className="results-section">
                  <div className="results-header">
                    <h3>
                      {sortedResults.length} Qualified Companies
                      {finalResult?.plan?.target_criteria?.industry && (
                        <span className="results-filter">
                          {' '}— {finalResult.plan.target_criteria.industry}
                        </span>
                      )}
                    </h3>
                    {(finalResult?.retry_count ?? 0) > 0 && (
                      <span className="retry-note">↺ {finalResult!.retry_count} retries</span>
                    )}
                  </div>
                  <div className="results-grid">
                    {sortedResults.map((ec, i) => (
                      <ResultCard key={ec.company.id} company={ec} rank={i + 1} />
                    ))}
                  </div>
                </div>
              )}

              {status === 'completed' && sortedResults.length === 0 && (
                <div className="empty-results">
                  <p>No matching companies found. Try broadening your criteria.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {status === 'idle' && (
          <div className="welcome">
            <h2>Multi-Agent GTM Intelligence</h2>
            <p>Powered by 5 AI agents: Planner → Retrieval → Enrichment → Validator → GTM Strategy</p>
            <div className="feature-chips">
              <span>🎯 ICP Scoring</span>
              <span>📈 Buying Signal Detection</span>
              <span>👤 Multi-Persona Outreach</span>
              <span>⚔️ Competitive Intelligence</span>
              <span>🔁 Self-Correcting Loop</span>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
