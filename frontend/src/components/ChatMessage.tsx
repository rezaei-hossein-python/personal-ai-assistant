import type { Message } from '../api/types'

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  return (
    <article className={`chat-message chat-message--${message.role}`}>
      <div className="chat-message__bubble">
        <span className="chat-message__role">
          {message.role === 'user' ? 'You' : 'Assistant'}
        </span>
        <p>{message.content}</p>
      </div>
    </article>
  )
}
