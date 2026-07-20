export interface RootResponse {
  message: string
}

export interface HealthResponse {
  application: string
  status: string
}

export interface ChatRequest {
  conversation_id: string
  message: string
}

export interface ChatResponse {
  response: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
