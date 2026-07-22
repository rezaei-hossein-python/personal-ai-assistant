import { ApiError, apiBaseUrl, fetchJson } from './http'
import type { ChatRequest, ChatResponse } from './types'

export function sendChat(request: ChatRequest, accessToken: string): Promise<ChatResponse> {
  return fetchJson<ChatResponse>('/chat', {
    method: 'POST',
    body: request,
    accessToken,
  })
}

export type ChatStreamEvent =
  | { event: 'start'; data: { conversation_id?: string } }
  | { event: 'delta'; data: { text: string } }
  | { event: 'complete'; data: ChatResponse & { conversation_id: string } }
  | { event: 'error'; data: { message: string } }

export interface ChatStreamHandlers {
  signal?: AbortSignal
  onDebug?: (event: string, detail?: Record<string, unknown>) => void
  onStart?: (data: { conversation_id?: string }) => void
  onDelta?: (text: string) => void
  onComplete?: (data: ChatResponse & { conversation_id: string }) => void
  onError?: (message: string) => void
}

export async function streamChat(
  request: ChatRequest,
  accessToken: string,
  handlers: ChatStreamHandlers = {},
): Promise<void> {
  handlers.onDebug?.('fetch_start')
  const response = await fetch(`${apiBaseUrl}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(request),
    signal: handlers.signal,
  })

  if (response.status === 401) {
    handlers.onDebug?.('fetch_unauthorized')
    throw new ApiError(401, 'Unauthorized', undefined)
  }

  if (!response.ok) {
    handlers.onDebug?.('fetch_not_ok', { status: response.status })
    throw new ApiError(response.status, `Request failed with status ${response.status}`, undefined)
  }

  if (!response.body) {
    handlers.onDebug?.('fetch_missing_body')
    throw new Error('Streaming is not supported by this browser.')
  }

  handlers.onDebug?.('fetch_body_opened', { status: response.status })
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      handlers.onDebug?.('fetch_read', { done, bytes: value?.byteLength ?? 0 })
      buffer += decoder.decode(value, { stream: !done })

      const frames = buffer.split(/\r?\n\r?\n/)
      buffer = frames.pop() ?? ''

      for (const frame of frames) {
        dispatchStreamFrame(frame, handlers)
      }

      if (done) {
        break
      }
    }

    if (buffer.trim()) {
      handlers.onDebug?.('fetch_final_buffer', { length: buffer.length })
      dispatchStreamFrame(buffer, handlers)
    }
  } finally {
    handlers.onDebug?.('fetch_release_lock')
    reader.releaseLock()
  }
}

export function parseChatStreamFrame(frame: string): ChatStreamEvent | null {
  const lines = frame.split(/\r?\n/)
  let eventName = ''
  const dataLines: string[] = []

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventName = line.slice('event:'.length).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trimStart())
    }
  }

  if (!eventName || dataLines.length === 0) {
    return null
  }

  let data: unknown
  try {
    data = JSON.parse(dataLines.join('\n')) as unknown
  } catch {
    return null
  }

  if (!data || typeof data !== 'object') {
    return null
  }

  if (eventName === 'start') {
    const conversationId = getOptionalString(data, 'conversation_id')
    return { event: 'start', data: { conversation_id: conversationId } }
  }

  if (eventName === 'delta') {
    const text = getRequiredString(data, 'text')
    return text === null ? null : { event: 'delta', data: { text } }
  }

  if (eventName === 'complete') {
    const response = getRequiredString(data, 'response')
    const conversationId = getRequiredString(data, 'conversation_id')
    if (response === null || conversationId === null) {
      return null
    }

    return {
      event: 'complete',
      data: {
        response,
        conversation_id: conversationId,
        metadata: getMetadata(data),
      },
    }
  }

  if (eventName === 'error') {
    const message = getRequiredString(data, 'message')
    return message === null ? null : { event: 'error', data: { message } }
  }

  return null
}

function dispatchStreamFrame(frame: string, handlers: ChatStreamHandlers) {
  handlers.onDebug?.('sse_frame', {
    event: getFrameEventName(frame),
    length: frame.length,
  })
  const parsed = parseChatStreamFrame(frame)

  if (!parsed) {
    handlers.onDebug?.('sse_malformed', { preview: frame.slice(0, 160) })
    handlers.onError?.('The streaming response contained malformed data.')
    return
  }

  handlers.onDebug?.('sse_event', { event: parsed.event })
  if (parsed.event === 'start') {
    handlers.onStart?.(parsed.data)
  } else if (parsed.event === 'delta') {
    handlers.onDelta?.(parsed.data.text)
  } else if (parsed.event === 'complete') {
    handlers.onComplete?.(parsed.data)
  } else {
    handlers.onError?.(parsed.data.message)
  }
}

function getFrameEventName(frame: string): string {
  const eventLine = frame.split(/\r?\n/).find((line) => line.startsWith('event:'))
  return eventLine ? eventLine.slice('event:'.length).trim() : ''
}

function getRequiredString(data: object, key: string): string | null {
  return key in data && typeof data[key as keyof typeof data] === 'string'
    ? String(data[key as keyof typeof data])
    : null
}

function getOptionalString(data: object, key: string): string | undefined {
  return key in data && typeof data[key as keyof typeof data] === 'string'
    ? String(data[key as keyof typeof data])
    : undefined
}

function getMetadata(data: object): ChatResponse['metadata'] {
  if (!('metadata' in data)) {
    return null
  }

  const metadata = data.metadata
  return metadata && typeof metadata === 'object' ? (metadata as ChatResponse['metadata']) : null
}
