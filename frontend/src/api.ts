import type { AskResponse, HealthResponse, IndexResponse } from './types'

async function check<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: 3, max_tokens: 2000 }),
  })
  return check<AskResponse>(response)
}

export async function indexPdf(file: File): Promise<IndexResponse> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch('/api/index', { method: 'POST', body: form })
  return check<IndexResponse>(response)
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health')
  return check<HealthResponse>(response)
}
