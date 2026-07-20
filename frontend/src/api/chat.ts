import { fetchJson } from './http'
import type { ChatRequest, ChatResponse } from './types'

export function sendChat(request: ChatRequest, accessToken: string): Promise<ChatResponse> {
  return fetchJson<ChatResponse>('/chat', {
    method: 'POST',
    body: request,
    accessToken,
  })
}
