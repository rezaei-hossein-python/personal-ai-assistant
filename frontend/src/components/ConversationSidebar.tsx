import type { ConversationSummary } from '../api/types'

interface ConversationSidebarProps {
  conversations: ConversationSummary[]
  activeConversationId: string | null
  error: string | null
  isLoading: boolean
  isDeleting: boolean
  onNewChat: () => void
  onSelect: (conversationId: string) => void
  onDelete: (conversationId: string) => void
}

export function ConversationSidebar({
  conversations,
  activeConversationId,
  error,
  isLoading,
  isDeleting,
  onNewChat,
  onSelect,
  onDelete,
}: ConversationSidebarProps) {
  return (
    <aside className="conversation-sidebar" aria-label="Conversation history">
      <div className="conversation-sidebar__header">
        <h2>History</h2>
        <button type="button" onClick={onNewChat}>
          New Chat
        </button>
      </div>

      {error ? (
        <p className="conversation-error" role="alert">
          {error}
        </p>
      ) : null}

      {isLoading ? <p className="conversation-status">Loading conversations...</p> : null}

      {!isLoading && conversations.length === 0 ? (
        <p className="conversation-status">No saved conversations yet.</p>
      ) : null}

      {conversations.length > 0 ? (
        <ul className="conversation-list">
          {conversations.map((conversation) => {
            const isActive = conversation.conversation_id === activeConversationId
            const label = getConversationLabel(conversation)

            return (
              <li key={conversation.conversation_id} className="conversation-list__item">
                <button
                  className={isActive ? 'conversation-list__select is-active' : 'conversation-list__select'}
                  type="button"
                  onClick={() => onSelect(conversation.conversation_id)}
                  aria-current={isActive ? 'true' : undefined}
                  title={label}
                >
                  <span>{label}</span>
                  <small>{conversation.message_count} messages</small>
                </button>
                <button
                  className="conversation-list__delete"
                  type="button"
                  onClick={() => onDelete(conversation.conversation_id)}
                  disabled={isDeleting}
                  aria-label={`Delete ${label}`}
                  title="Delete"
                >
                  X
                </button>
              </li>
            )
          })}
        </ul>
      ) : null}
    </aside>
  )
}

function getConversationLabel(conversation: ConversationSummary): string {
  const firstMessage = conversation.first_user_message?.trim()
  const title = conversation.title?.trim()

  if (title && title !== 'New Conversation') {
    return title
  }

  if (firstMessage) {
    return firstMessage.length > 48 ? `${firstMessage.slice(0, 45)}...` : firstMessage
  }

  return 'New conversation'
}
