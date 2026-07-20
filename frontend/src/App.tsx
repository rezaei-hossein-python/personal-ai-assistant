import { useEffect, useState } from 'react'
import './App.css'
import { getHealth } from './api/health'
import { ChatInput } from './components/ChatInput'
import { ChatMessage, type Message } from './components/ChatMessage'

type BackendStatus = 'loading' | 'connected' | 'unavailable'

const temporaryAssistantResponse =
  'Chat backend integration will be connected in the next step.'

function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('loading')
  const [messages, setMessages] = useState<Message[]>([])

  useEffect(() => {
    let isMounted = true

    getHealth()
      .then(() => {
        if (isMounted) {
          setBackendStatus('connected')
        }
      })
      .catch(() => {
        if (isMounted) {
          setBackendStatus('unavailable')
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  function handleSubmitMessage(content: string) {
    setMessages((currentMessages) => [
      ...currentMessages,
      { role: 'user', content },
      { role: 'assistant', content: temporaryAssistantResponse },
    ])
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <h1>Personal AI Assistant</h1>
          <p>Ask a question or start a conversation.</p>
        </div>
        <p className={`backend-status backend-status--${backendStatus}`}>
          <span className="backend-status__indicator" aria-hidden="true" />
          {getBackendStatusText(backendStatus)}
        </p>
      </header>

      <section className="chat-panel" aria-label="Conversation">
        <div className="message-list">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h2>Ready when you are.</h2>
              <p>Your messages will appear here while the chat backend is connected in a later step.</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <ChatMessage key={`${message.role}-${index}`} message={message} />
            ))
          )}
        </div>
        <ChatInput onSubmit={handleSubmitMessage} />
      </section>
    </main>
  )
}

function getBackendStatusText(status: BackendStatus): string {
  if (status === 'connected') {
    return 'Backend connected'
  }

  if (status === 'unavailable') {
    return 'Backend unavailable'
  }

  return 'Checking backend...'
}

export default App
