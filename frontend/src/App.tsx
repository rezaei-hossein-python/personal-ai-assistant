import { useEffect, useState } from 'react'
import './App.css'
import { login } from './api/auth'
import { sendChat } from './api/chat'
import { getHealth } from './api/health'
import { ChatInput } from './components/ChatInput'
import { ChatMessage, type Message } from './components/ChatMessage'
import { LoginForm } from './components/LoginForm'

type BackendStatus = 'loading' | 'connected' | 'unavailable'

function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('loading')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loginError, setLoginError] = useState<string | null>(null)
  const [chatError, setChatError] = useState<string | null>(null)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [isSendingMessage, setIsSendingMessage] = useState(false)

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

  async function handleLogin(email: string, password: string) {
    setIsLoggingIn(true)
    setLoginError(null)

    try {
      const tokenResponse = await login({ email, password })
      setAccessToken(tokenResponse.access_token)
      setConversationId(createConversationId())
      setMessages([])
      setChatError(null)
    } catch (error) {
      setLoginError(getErrorText(error, 'Unable to sign in. Check your credentials and try again.'))
    } finally {
      setIsLoggingIn(false)
    }
  }

  async function handleSubmitMessage(content: string) {
    if (!accessToken || !conversationId || isSendingMessage) {
      return
    }

    setMessages((currentMessages) => [
      ...currentMessages,
      { role: 'user', content },
    ])
    setChatError(null)
    setIsSendingMessage(true)

    try {
      const chatResponse = await sendChat(
        {
          conversation_id: conversationId,
          message: content,
        },
        accessToken,
      )

      setMessages((currentMessages) => [
        ...currentMessages,
        { role: 'assistant', content: chatResponse.response },
      ])
    } catch (error) {
      setChatError(getErrorText(error, 'Unable to send message. Try again.'))
    } finally {
      setIsSendingMessage(false)
    }
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

      {accessToken ? (
        <section className="chat-panel" aria-label="Conversation">
          <div className="message-list">
            {messages.length === 0 ? (
              <div className="empty-state">
                <h2>Ready when you are.</h2>
                <p>Your messages will appear here after you send them to the assistant.</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <ChatMessage key={`${message.role}-${index}`} message={message} />
              ))
            )}

            {isSendingMessage ? (
              <p className="thinking-state" aria-live="polite">
                Assistant is thinking...
              </p>
            ) : null}
          </div>

          {chatError ? (
            <p className="chat-error" role="alert">
              {chatError}
            </p>
          ) : null}

          <ChatInput onSubmit={handleSubmitMessage} disabled={isSendingMessage} />
        </section>
      ) : (
        <LoginForm error={loginError} isSubmitting={isLoggingIn} onSubmit={handleLogin} />
      )}
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

function createConversationId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }

  return `conversation-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function getErrorText(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallback
}

export default App
