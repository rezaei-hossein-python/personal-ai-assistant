import { fetchJson } from './http'
import type { MemoryCreateRequest, MemoryResponse } from './types'

export function listMemories(accessToken: string): Promise<MemoryResponse[]> {
  return fetchJson<MemoryResponse[]>('/memories', {
    method: 'GET',
    accessToken,
  })
}

export function createMemory(
  request: MemoryCreateRequest,
  accessToken: string,
): Promise<MemoryResponse> {
  return fetchJson<MemoryResponse>('/memories', {
    method: 'POST',
    body: request,
    accessToken,
  })
}

export function deleteMemory(memoryId: number, accessToken: string): Promise<{ message: string }> {
  return fetchJson<{ message: string }>(`/memories/${memoryId}`, {
    method: 'DELETE',
    accessToken,
  })
}
