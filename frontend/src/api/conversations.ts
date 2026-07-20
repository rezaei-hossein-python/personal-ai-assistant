import { fetchJson } from './http'
import type { ConversationDetail, ConversationSummary } from './types'

export function listConversations(accessToken: string): Promise<ConversationSummary[]> {
  return fetchJson<ConversationSummary[]>('/conversations', {
    accessToken,
  })
}

export function getConversation(
  conversationId: string,
  accessToken: string,
): Promise<ConversationDetail> {
  return fetchJson<ConversationDetail>(`/conversations/${encodeURIComponent(conversationId)}`, {
    accessToken,
  })
}

export function deleteConversation(
  conversationId: string,
  accessToken: string,
): Promise<{ message: string }> {
  return fetchJson<{ message: string }>(`/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'DELETE',
    accessToken,
  })
}
