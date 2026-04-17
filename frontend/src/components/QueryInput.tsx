import React, { useState, useRef, useEffect } from 'react'

const EXAMPLE_QUERIES = [
  'Find high-growth AI SaaS companies in the US and generate personalized outbound hooks for their VP Sales',
  'Identify Series B fintech startups hiring aggressively and suggest outreach strategies',
  'Find developer tools companies that recently raised funding and generate outreach for CTOs',
  'Give me mid-market SaaS companies likely to displace competitors and how to target their CEO',
]

interface QueryInputProps {
  onSubmit: (query: string) => void
  disabled?: boolean
  onReset?: () => void
  isStreaming?: boolean
}

export function QueryInput({ onSubmit, disabled, onReset, isStreaming }: QueryInputProps) {
  const [query, setQuery] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
  }, [query])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (!q || disabled) return
    onSubmit(q)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit(e as unknown as React.FormEvent)
    }
  }

  return (
    <div className="query-input-container">
      <form onSubmit={handleSubmit} className="query-form">
        <div className="textarea-wrapper">
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your GTM query... (e.g. 'Find Series B SaaS companies in the US hiring VP Sales')"
            disabled={disabled}
            rows={2}
            className="query-textarea"
          />
          <div className="textarea-hint">Ctrl+Enter to submit</div>
        </div>

        <div className="query-actions">
          <button
            type="submit"
            disabled={disabled || !query.trim()}
            className="btn btn-primary"
          >
            {isStreaming ? (
              <>
                <span className="spinner" />
                Running...
              </>
            ) : (
              'Run GTM Query'
            )}
          </button>
          {onReset && (
            <button type="button" onClick={onReset} className="btn btn-secondary">
              Reset
            </button>
          )}
        </div>
      </form>

      {!disabled && (
        <div className="example-queries">
          <span className="example-label">Try:</span>
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              className="example-chip"
              onClick={() => setQuery(q)}
              type="button"
            >
              {q.length > 60 ? q.slice(0, 60) + '…' : q}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
