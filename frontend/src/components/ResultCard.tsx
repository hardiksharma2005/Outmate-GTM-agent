import { useState } from 'react'
import type { EnrichedCompany } from '../types/gtm'

interface ResultCardProps {
  company: EnrichedCompany
  rank: number
}

const TIER_CLASS: Record<string, string> = {
  'Tier 1 - Hot': 'tier-hot',
  'Tier 2 - Warm': 'tier-warm',
  'Tier 3 - Nurture': 'tier-nurture',
  'Excluded': 'tier-excluded',
}

const SIGNAL_ICONS: Record<string, string> = {
  RECENT_FUNDING: '💰',
  HIGH_GROWTH: '🚀',
  HIRING_EXPANSION: '👥',
  HIRING_SALES_ROLES: '🎯',
  SERIES_SWEET_SPOT: '⭐',
  TECH_FIT: '🔧',
  COMPETITIVE_DISPLACEMENT: '⚔️',
}

export function ResultCard({ company: ec, rank }: ResultCardProps) {
  const [expanded, setExpanded] = useState(false)
  const c = ec.company
  const icp = ec.icp_score
  const tierCls = TIER_CLASS[icp.tier] || 'tier-nurture'

  return (
    <div className={`result-card ${tierCls}`}>
      <div className="card-rank">#{rank}</div>

      <div className="card-main">
        <div className="card-header">
          <div>
            <h4 className="card-company-name">{c.name}</h4>
            <span className="card-domain">{c.domain}</span>
          </div>
          <div className="card-badges">
            <span className={`tier-badge ${tierCls}`}>{icp.tier}</span>
            <span className="stage-badge">{c.funding_stage}</span>
            <span className="size-badge">{c.company_size.toLocaleString()} emp</span>
          </div>
        </div>

        <p className="card-description">{c.description || 'No description available'}</p>

        {/* ICP score bar */}
        <div className="icp-bar-row">
          <span className="icp-label">ICP Score</span>
          <div className="icp-bar-track">
            <div
              className="icp-bar-fill"
              style={{ width: `${Math.round(icp.composite * 100)}%` }}
            />
          </div>
          <span className="icp-value">{Math.round(icp.composite * 100)}%</span>
        </div>

        {/* Signals */}
        {ec.signals.length > 0 && (
          <div className="signal-chips">
            {ec.signals.slice(0, 4).map((sig) => (
              <span key={sig.type} className="signal-chip" title={sig.evidence}>
                {SIGNAL_ICONS[sig.type] || '•'} {sig.label}
              </span>
            ))}
          </div>
        )}

        {/* Why this result toggle */}
        <button
          className="why-button"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? '▲ Hide explanation' : '▼ Why this result?'}
        </button>

        {expanded && (
          <div className="why-explanation">
            <p>{icp.explanation}</p>

            <div className="icp-breakdown">
              <div className="icp-dim">
                <span>Fit</span>
                <div className="dim-bar">
                  <div style={{ width: `${Math.round(icp.fit * 100)}%`, background: '#60a5fa' }} />
                </div>
                <span>{Math.round(icp.fit * 100)}%</span>
              </div>
              <div className="icp-dim">
                <span>Intent</span>
                <div className="dim-bar">
                  <div style={{ width: `${Math.round(icp.intent * 100)}%`, background: '#f59e0b' }} />
                </div>
                <span>{Math.round(icp.intent * 100)}%</span>
              </div>
              <div className="icp-dim">
                <span>Growth</span>
                <div className="dim-bar">
                  <div style={{ width: `${Math.round(icp.growth * 100)}%`, background: '#22c55e' }} />
                </div>
                <span>{Math.round(icp.growth * 100)}%</span>
              </div>
            </div>

            {ec.signals.length > 0 && (
              <div className="full-signals">
                <strong>Buying Signals:</strong>
                <ul>
                  {ec.signals.map((sig) => (
                    <li key={sig.type}>
                      <strong>{sig.label}:</strong> {sig.evidence}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {ec.enrichment_notes && (
              <div className="enrichment-notes">
                <strong>Sales Context:</strong> {ec.enrichment_notes}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
