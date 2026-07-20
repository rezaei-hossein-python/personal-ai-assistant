import { fetchJson } from './http'
import type { HealthResponse } from './types'

export function getHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>('/health')
}
