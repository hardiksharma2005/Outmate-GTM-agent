import type { GTMResponse } from '../types/gtm'

const BASE = '/api'

export async function submitQuery(query: string): Promise<{ session_id: string }> {
  const res = await fetch(`${BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getResult(sessionId: string): Promise<GTMResponse | null> {
  const res = await fetch(`${BASE}/result/${sessionId}`)
  if (res.status === 202) return null
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
