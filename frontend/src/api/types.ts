export interface HealthResponse {
  application: string
  status: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  metadata?: ChatResponseMetadata | null
}

export interface ChatRequest {
  conversation_id: string
  message: string
  knowledge_retrieval?: boolean | null
}

export interface ChatResponse {
  response: string
  metadata: ChatResponseMetadata | null
}

export type KnowledgeMode = 'auto' | 'always' | 'never'

export type KnowledgeRetrievalMode = 'planner' | 'explicit_enabled' | 'explicit_disabled'

export interface KnowledgeSource {
  document_id: number
  document_name: string
  chunk_id: number
  chunk_index: number
  start_character: number | null
  end_character: number | null
  distance: number | null
}

export interface KnowledgeRetrievalMetadata {
  enabled: boolean
  mode: KnowledgeRetrievalMode
  retrieval_count: number
  sources: KnowledgeSource[]
  warning: string | null
}

export interface ChatResponseMetadata {
  knowledge: KnowledgeRetrievalMetadata | null
}

export type DocumentProcessingStatus = 'processing' | 'completed' | 'failed' | string

export interface DocumentResponse {
  id: number
  original_filename: string
  content_type: string
  file_size: number
  processing_status: DocumentProcessingStatus
  error_message: string | null
  metadata: Record<string, unknown>
  uploaded_at: string | null
}

export interface DocumentSearchRequest {
  query: string
  limit?: number
}

export interface DocumentSearchResult {
  document_id: number
  document_name: string
  chunk_id: number
  chunk_index: number
  content: string
  metadata: Record<string, unknown>
  start_character: number | null
  end_character: number | null
  distance: number | null
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
