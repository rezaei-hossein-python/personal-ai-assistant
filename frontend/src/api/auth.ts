import { fetchJson } from './http'
import type { LoginRequest, RegisterRequest, TokenResponse, UserResponse } from './types'

export function login(request: LoginRequest): Promise<TokenResponse> {
  return fetchJson<TokenResponse>('/auth/login', {
    method: 'POST',
    body: request,
  })
}

export function register(request: RegisterRequest): Promise<UserResponse> {
  return fetchJson<UserResponse>('/auth/register', {
    method: 'POST',
    body: request,
  })
}
