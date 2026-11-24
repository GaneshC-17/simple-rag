export interface Source {
  content: string
  source: string
  chunk_index: number
  similarity: number
}

export interface AskResponse {
  answer: string
  sources: Source[]
}

export interface IndexResponse {
  source: string
  pages: number
  chunks: number
  tokens: number
}

export interface HealthResponse {
  status: string
  chunks: number
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  answer: string
  sources?: Source[]
}
