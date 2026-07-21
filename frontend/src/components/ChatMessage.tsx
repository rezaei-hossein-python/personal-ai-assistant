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

  const author = message.role === 'user' ? 'You' : 'Assistant'

  return (
    <article
      className={`chat-message chat-message--${message.role}`}
      aria-label={`${author} message`}
    >
      <div className="chat-message__bubble">
        <span className="chat-message__role">
          {author}
        </span>
        {usedMemory ? (
          <span className="memory-used">
            Used memory: {message.metadata?.memory?.retrieval_count} saved{' '}
            {(message.metadata?.memory?.retrieval_count ?? 0) === 1 ? 'memory' : 'memories'}
          </span>
        ) : null}
        {actionSummaries.length > 0 ? (
          <ul className="tool-used-list" aria-label="Tool use">
            {actionSummaries.map((action) => (
              <li
                className={`tool-used tool-used--${action.status}`}
                key={`${action.tool_name}-${action.summary}`}
              >
                Tool {action.status}: {action.summary}
              </li>
            ))}
          </ul>
        ) : null}
        <p>{message.content}</p>
        {message.role === 'assistant' ? <KnowledgeSources metadata={message.metadata} /> : null}
      </div>
    </article>
  )
}
