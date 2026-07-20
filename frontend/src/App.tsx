import { useEffect, useRef, useState } from 'react'
import './App.css'
import { login } from './api/auth'
import { sendChat } from './api/chat'
import { listDocuments, uploadDocument } from './api/documents'
import { getHealth } from './api/health'
import { ApiError } from './api/http'
import { createMemory, deleteMemory, listMemories } from './api/memories'
import type { DocumentResponse, KnowledgeMode, MemoryMode, MemoryResponse, Message } from './api/types'
import { ChatInput } from './components/ChatInput'
import { ChatMessage } from './components/ChatMessage'
import { DocumentList } from './components/DocumentList'
import { DocumentUpload } from './components/DocumentUpload'
import { KnowledgeModeSelector } from './components/KnowledgeModeSelector'
import { LoginForm } from './components/LoginForm'
import { MemoryModeSelector } from './components/MemoryModeSelector'
import { MemorySection } from './components/MemorySection'

type BackendStatus = 'loading' | 'connected' | 'unavailable'

function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('loading')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [documents, setDocuments] = useState<DocumentResponse[]>([])
  const [memories, setMemories] = useState<MemoryResponse[]>([])
  const [knowledgeMode, setKnowledgeMode] = useState<KnowledgeMode>('auto')
  const [memoryMode, setMemoryMode] = useState<MemoryMode>('auto')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [chatError, setChatError] = useState<string | null>(null)
  const [documentError, setDocumentError] = useState<string | null>(null)
  const [memoryError, setMemoryError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [isSendingMessage, setIsSendingMessage] = useState(false)
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false)
  const [isLoadingMemories, setIsLoadingMemories] = useState(false)
  const [isUploadingDocument, setIsUploadingDocument] = useState(false)
  const [isCreatingMemory, setIsCreatingMemory] = useState(false)
  const [isDeletingMemory, setIsDeletingMemory] = useState(false)
  const isSendingMessageRef = useRef(false)

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

  function clearSession() {
    isSendingMessageRef.current = false
    setAccessToken(null)
    setConversationId(null)
    setMessages([])
    setDocuments([])
    setMemories([])
    setKnowledgeMode('auto')
    setMemoryMode('auto')
    setLoginError(null)
    setChatError(null)
    setDocumentError(null)
    setMemoryError(null)
    setUploadError(null)
    setIsSendingMessage(false)
    setIsLoadingDocuments(false)
    setIsLoadingMemories(false)
    setIsUploadingDocument(false)
    setIsCreatingMemory(false)
    setIsDeletingMemory(false)
  }

  async function handleLogin(email: string, password: string) {
    setIsLoggingIn(true)
    setLoginError(null)

    try {
      const tokenResponse = await login({ email, password })
      setAccessToken(tokenResponse.access_token)
      setConversationId(createConversationId())
      setMessages([])
      setChatError(null)
      setDocumentError(null)
      setMemoryError(null)
      setUploadError(null)
      await Promise.all([
        loadDocuments(tokenResponse.access_token),
        loadMemories(tokenResponse.access_token),
      ])
    } catch (error) {
      setLoginError(getLoginErrorText(error))
    } finally {
      setIsLoggingIn(false)
    }
  }

  function handleLogout() {
    clearSession()
  }

  function handleSessionExpired() {
    clearSession()
    setLoginError('Your session expired. Sign in again to continue.')
  }

  async function loadDocuments(token: string) {
    setIsLoadingDocuments(true)
    setDocumentError(null)

    try {
      const documentResponse = await listDocuments(token)
      setDocuments(documentResponse)
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setDocumentError(getDocumentErrorText(error))
    } finally {
      setIsLoadingDocuments(false)
    }
  }

  async function loadMemories(token: string) {
    setIsLoadingMemories(true)
    setMemoryError(null)

    try {
      const memoryResponse = await listMemories(token)
      setMemories(memoryResponse)
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setMemoryError(getMemoryErrorText(error))
    } finally {
      setIsLoadingMemories(false)
    }
  }

  async function handleUploadDocument(file: File) {
    if (!accessToken || isUploadingDocument) {
      return
    }

    setIsUploadingDocument(true)
    setUploadError(null)

    try {
      const uploadedDocument = await uploadDocument(file, accessToken)
      await loadDocuments(accessToken)

      if (uploadedDocument.processing_status === 'failed') {
        setUploadError(uploadedDocument.error_message ?? 'Document processing failed.')
      }
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setUploadError(getDocumentErrorText(error))
    } finally {
      setIsUploadingDocument(false)
    }
  }

  async function handleCreateMemory(category: string, key: string, value: string): Promise<boolean> {
    if (!accessToken || isCreatingMemory) {
      return false
    }

    setIsCreatingMemory(true)
    setMemoryError(null)

    try {
      await createMemory({ category, key, value }, accessToken)
      await loadMemories(accessToken)
      return true
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return false
      }

      setMemoryError(getMemoryErrorText(error))
      return false
    } finally {
      setIsCreatingMemory(false)
    }
  }

  async function handleDeleteMemory(memoryId: number) {
    if (!accessToken || isDeletingMemory) {
      return
    }

    setIsDeletingMemory(true)
    setMemoryError(null)

    try {
      await deleteMemory(memoryId, accessToken)
      await loadMemories(accessToken)
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setMemoryError(getMemoryErrorText(error))
    } finally {
      setIsDeletingMemory(false)
    }
  }

  async function handleSubmitMessage(content: string) {
    if (!accessToken || !conversationId || isSendingMessageRef.current) {
      return
    }

    isSendingMessageRef.current = true
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
          knowledge_retrieval: getKnowledgeRetrievalValue(knowledgeMode),
          memory_retrieval: getMemoryRetrievalValue(memoryMode),
        },
        accessToken,
      )

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: 'assistant',
          content: chatResponse.response,
          metadata: chatResponse.metadata,
        },
      ])
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setChatError(getChatErrorText(error))
    } finally {
      isSendingMessageRef.current = false
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
        <div className="app-header__actions">
          <p className={`backend-status backend-status--${backendStatus}`}>
            <span className="backend-status__indicator" aria-hidden="true" />
            {getBackendStatusText(backendStatus)}
          </p>
          {accessToken ? (
            <button className="logout-button" type="button" onClick={handleLogout}>
              Logout
            </button>
          ) : null}
        </div>
      </header>

      {accessToken ? (
        <section className="chat-panel" aria-label="Conversation">
          <div className="knowledge-panel">
            <div className="knowledge-panel__controls">
              <DocumentUpload
                error={uploadError}
                isUploading={isUploadingDocument}
                onUpload={handleUploadDocument}
              />
              <KnowledgeModeSelector
                mode={knowledgeMode}
                onChange={setKnowledgeMode}
                disabled={isSendingMessage}
              />
              <MemoryModeSelector
                mode={memoryMode}
                onChange={setMemoryMode}
                disabled={isSendingMessage}
              />
            </div>
            <MemorySection
              memories={memories}
              error={memoryError}
              isCreating={isCreatingMemory}
              isDeleting={isDeletingMemory}
              isLoading={isLoadingMemories}
              onCreate={handleCreateMemory}
              onDelete={handleDeleteMemory}
            />
            <DocumentList
              documents={documents}
              error={documentError}
              isLoading={isLoadingDocuments}
            />
          </div>

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

function getKnowledgeRetrievalValue(mode: KnowledgeMode): boolean | null {
  if (mode === 'always') {
    return true
  }

  if (mode === 'never') {
    return false
  }

  return null
}

function getMemoryRetrievalValue(mode: MemoryMode): boolean | null {
  if (mode === 'always') {
    return true
  }

  if (mode === 'never') {
    return false
  }

  return null
}

function getLoginErrorText(error: unknown): string {
  if (isAuthenticationError(error)) {
    return 'Invalid email or password.'
  }

  if (isNetworkError(error)) {
    return 'Cannot reach the backend. Try again shortly.'
  }

  if (error instanceof ApiError) {
    return 'Unable to sign in. Try again.'
  }

  return 'Unable to sign in. Check your credentials and try again.'
}

function getChatErrorText(error: unknown): string {
  if (isNetworkError(error)) {
    return 'Cannot reach the backend. Your conversation was kept.'
  }

  if (error instanceof ApiError) {
    return 'Unable to send message. Your conversation was kept.'
  }

  return 'Unable to send message. Try again.'
}

function getDocumentErrorText(error: unknown): string {
  if (isNetworkError(error)) {
    return 'Cannot reach the backend. Try again shortly.'
  }

  if (error instanceof ApiError) {
    return error.message
  }

  return 'Unable to update documents. Try again.'
}

function getMemoryErrorText(error: unknown): string {
  if (isNetworkError(error)) {
    return 'Cannot reach the backend. Try again shortly.'
  }

  if (error instanceof ApiError) {
    return error.message
  }

  return 'Unable to update memories. Try again.'
}

function isAuthenticationError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

function isNetworkError(error: unknown): boolean {
  return error instanceof TypeError
}

export default App
