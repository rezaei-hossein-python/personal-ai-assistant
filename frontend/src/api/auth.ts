import { fetchJson } from './http'
import type { LoginRequest, TokenResponse } from './types'

export function login(request: LoginRequest): Promise<TokenResponse> {
  return fetchJson<TokenResponse>('/auth/login', {
    method: 'POST',
    body: request,
  })
}
