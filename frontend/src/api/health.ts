import { fetchJson } from './http'
import type { HealthResponse, RootResponse } from './types'

export function getRoot(): Promise<RootResponse> {
  return fetchJson<RootResponse>('/')
}

export function getHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>('/health')
}
