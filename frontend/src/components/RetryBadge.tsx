interface RetryBadgeProps {
  count: number
  reason?: string
  maxRetries?: number
}

export function RetryBadge({ count, reason, maxRetries = 3 }: RetryBadgeProps) {
  if (count === 0) return null
  return (
    <span className="retry-badge" title={reason || `Retried ${count} time(s)`}>
      ↺ {count}/{maxRetries}
    </span>
  )
}
