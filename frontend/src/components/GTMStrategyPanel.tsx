import { useState } from 'react'
import type { GTMStrategy } from '../types/gtm'

interface GTMStrategyPanelProps {
  strategy: GTMStrategy
}

export function GTMStrategyPanel({ strategy }: GTMStrategyPanelProps) {
  const [activeTab, setActiveTab] = useState<'hooks' | 'emails' | 'personas' | 'insights'>('hooks')

  return (
    <div className="gtm-strategy-panel">
      <h3>GTM Strategy</h3>

      <div className="strategy-tabs">
        {(['hooks', 'emails', 'personas', 'insights'] as const).map((tab) => (
          <button
            key={tab}
            className={`tab-btn ${activeTab === tab ? 'tab-active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'hooks' && `🎣 Hooks (${strategy.hooks.length})`}
            {tab === 'emails' && `✉️ Emails (${strategy.email_snippets.length})`}
            {tab === 'personas' && `👤 Personas (${strategy.persona_plays.length})`}
            {tab === 'insights' && `💡 Insights`}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === 'hooks' && (
          <div className="hooks-list">
            {strategy.hooks.map((hook, i) => (
              <div key={i} className="hook-card">
                <span className="hook-num">{i + 1}</span>
                <p>{hook}</p>
              </div>
            ))}
            {strategy.angles.length > 0 && (
              <>
                <h4>Strategic Angles</h4>
                {strategy.angles.map((angle, i) => (
                  <div key={i} className="angle-item">• {angle}</div>
                ))}
              </>
            )}
            {strategy.competitive_positioning.length > 0 && (
              <>
                <h4>Competitive Positioning</h4>
                {strategy.competitive_positioning.map((pos, i) => (
                  <div key={i} className="positioning-item">⚔️ {pos}</div>
                ))}
              </>
            )}
          </div>
        )}

        {activeTab === 'emails' && (
          <div className="emails-list">
            {strategy.email_snippets.map((snippet, i) => (
              <div key={i} className="email-card">
                <div className="email-header">
                  <span className="email-persona">{snippet.persona}</span>
                  <span className="email-subject">{snippet.subject}</span>
                </div>
                <div className="email-body">
                  <p><strong>Opening:</strong> {snippet.opening}</p>
                  <p><strong>Value Prop:</strong> {snippet.value_prop}</p>
                  <p><strong>CTA:</strong> {snippet.cta}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'personas' && (
          <div className="personas-list">
            {strategy.persona_plays.map((play, i) => (
              <div key={i} className="persona-card">
                <h4>{play.persona}</h4>
                {play.pain_points.length > 0 && (
                  <div className="persona-section">
                    <strong>Pain Points:</strong>
                    <ul>{play.pain_points.map((p, j) => <li key={j}>{p}</li>)}</ul>
                  </div>
                )}
                {play.value_angles.length > 0 && (
                  <div className="persona-section">
                    <strong>Value Angles:</strong>
                    <ul>{play.value_angles.map((v, j) => <li key={j}>{v}</li>)}</ul>
                  </div>
                )}
                {play.objection_handles.length > 0 && (
                  <div className="persona-section">
                    <strong>Objection Handles:</strong>
                    <ul>{play.objection_handles.map((o, j) => <li key={j}>{o}</li>)}</ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'insights' && (
          <div className="insights-list">
            <h4>ICP Insights</h4>
            {strategy.icp_insights.map((insight, i) => (
              <div key={i} className="insight-item">💡 {insight}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
