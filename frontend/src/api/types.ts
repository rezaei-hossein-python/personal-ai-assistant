export interface HealthResponse {
  application: string
  status: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  clientId?: string
  metadata?: ChatResponseMetadata | null
  isIncomplete?: boolean
  created_at?: string | null
}

export interface ChatRequest {
  conversation_id: string
  message: string
  knowledge_retrieval?: boolean | null
  memory_retrieval?: boolean | null
}

export interface ChatResponse {
  response: string
  metadata: ChatResponseMetadata | null
}

export type KnowledgeMode = 'auto' | 'always' | 'never'
export type MemoryMode = 'auto' | 'always' | 'never'

export type KnowledgeRetrievalMode = 'planner' | 'explicit_enabled' | 'explicit_disabled'
export type MemoryRetrievalMode = 'planner' | 'explicit_enabled' | 'explicit_disabled'

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

export interface MemorySource {
  category: string
  key: string
}

export interface MemoryRetrievalMetadata {
  enabled: boolean
  mode: MemoryRetrievalMode
  retrieval_count: number
  sources: MemorySource[]
}

export interface ChatResponseMetadata {
  knowledge: KnowledgeRetrievalMetadata | null
  memory: MemoryRetrievalMetadata | null
  actions?: ActionExecutionMetadata[]
}

export interface ActionExecutionMetadata {
  tool_name: string
  status: 'success' | 'error'
  summary: string
}

export interface MemoryCreateRequest {
  category: string
  key: string
  value: string
}

export interface MemoryResponse {
  id: number
  user_id: number
  category: string
  key: string
  value: string
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

export interface RegisterRequest {
  email: string
  name: string
  password: string
}

export interface UserResponse {
  id: number
  email: string
  name: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface ConversationMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  response_metadata?: ChatResponseMetadata | null
  created_at: string | null
}

export interface ConversationSummary {
  conversation_id: string
  title: string
  created_at: string | null
  updated_at: string | null
  message_count: number
  first_user_message: string | null
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[]
}

export interface DesktopStatusResponse {
  desktop_mode: boolean
  app_version: string
  data_directory: string
  logs_directory: string
  database_backend: string
  backend_status: string
  openai_api_key_configured: boolean
}

export interface SecretStatusResponse {
  configured: boolean
  masked: string | null
}

export interface TestOpenAIKeyResponse {
  configured: boolean
  valid: boolean
  message: string
}
