import type { Message } from '../api/types'
import { KnowledgeSources } from './KnowledgeSources'

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const usedMemory =
    message.role === 'assistant' &&
    Boolean(message.metadata?.memory?.enabled) &&
    (message.metadata?.memory?.retrieval_count ?? 0) > 0
  const actionSummaries =
    message.role === 'assistant'
      ? (message.metadata?.actions ?? []).filter((action) => action.summary)
      : []

  return (
    <article className={`chat-message chat-message--${message.role}`}>
      <div className="chat-message__bubble">
        <span className="chat-message__role">
          {message.role === 'user' ? 'You' : 'Assistant'}
        </span>
        {usedMemory ? <span className="memory-used">Used memory</span> : null}
        {actionSummaries.map((action) => (
          <span
            className={`tool-used tool-used--${action.status}`}
            key={`${action.tool_name}-${action.summary}`}
          >
            {action.summary}
          </span>
        ))}
        <p>{message.content}</p>
        {message.role === 'assistant' ? <KnowledgeSources metadata={message.metadata} /> : null}
      </div>
    </article>
  )
}
