import { useEffect, useRef, useCallback } from 'react'
import type { AgentEvent } from '../types/gtm'

interface UseSSEOptions {
  onEvent: (event: AgentEvent) => void
  onError?: (err: Event) => void
  onClose?: () => void
}

export function useSSE(sessionId: string | null, options: UseSSEOptions) {
  const esRef = useRef<EventSource | null>(null)
  const { onEvent, onError, onClose } = options
  const retryCount = useRef(0)
  const maxRetries = 5

  const connect = useCallback(() => {
    if (!sessionId) return
    if (esRef.current) {
      esRef.current.close()
    }

    const es = new EventSource(`/api/stream/${sessionId}`)
    esRef.current = es

    es.onmessage = (e) => {
      try {
        const event: AgentEvent = JSON.parse(e.data)
        retryCount.current = 0
        onEvent(event)
        if (event.event_type === 'FINAL_OUTPUT' || event.event_type === 'ERROR') {
          es.close()
          esRef.current = null
          onClose?.()
        }
      } catch {
        // Heartbeat or non-JSON — ignore
      }
    }

    es.onerror = (err) => {
      onError?.(err)
      es.close()
      esRef.current = null

      if (retryCount.current < maxRetries) {
        retryCount.current++
        const delay = Math.min(1000 * 2 ** retryCount.current, 10000)
        setTimeout(connect, delay)
      }
    }
  }, [sessionId, onEvent, onError, onClose])

  useEffect(() => {
    connect()
    return () => {
      esRef.current?.close()
      esRef.current = null
    }
  }, [connect])
}
