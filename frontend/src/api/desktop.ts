import { fetchJson } from './http'
import type {
  DesktopStatusResponse,
  SecretStatusResponse,
  TestOpenAIKeyResponse,
} from './types'

export function getDesktopStatus(): Promise<DesktopStatusResponse> {
  return fetchJson<DesktopStatusResponse>('/desktop/status')
}

export function getOpenAIKeyStatus(): Promise<SecretStatusResponse> {
  return fetchJson<SecretStatusResponse>('/desktop/secrets/openai')
}

export function saveOpenAIKey(apiKey: string): Promise<SecretStatusResponse> {
  return fetchJson<SecretStatusResponse>('/desktop/secrets/openai', {
    method: 'PUT',
    body: { api_key: apiKey },
  })
}

export function removeOpenAIKey(): Promise<SecretStatusResponse> {
  return fetchJson<SecretStatusResponse>('/desktop/secrets/openai', {
    method: 'DELETE',
  })
}

export function testOpenAIKey(): Promise<TestOpenAIKeyResponse> {
  return fetchJson<TestOpenAIKeyResponse>('/desktop/secrets/openai/test', {
    method: 'POST',
  })
}
