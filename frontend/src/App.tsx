import { useEffect, useRef, useState } from 'react'
import './App.css'
import { login, register } from './api/auth'
import { sendChat } from './api/chat'
import {
  deleteConversation,
  getConversation,
  listConversations,
} from './api/conversations'
import {
  getDesktopStatus,
  getOpenAIKeyStatus,
  removeOpenAIKey,
  saveOpenAIKey,
  testOpenAIKey,
} from './api/desktop'
import { listDocuments, uploadDocument } from './api/documents'
import { getHealth } from './api/health'
import { ApiError } from './api/http'
import { createMemory, deleteMemory, listMemories } from './api/memories'
import type {
  ConversationSummary,
  DesktopStatusResponse,
  DocumentResponse,
  KnowledgeMode,
  MemoryMode,
  MemoryResponse,
  Message,
  SecretStatusResponse,
} from './api/types'
import { ChatInput, type ChatInputHandle } from './components/ChatInput'
import { ChatMessage } from './components/ChatMessage'
import { ConversationSidebar } from './components/ConversationSidebar'
import { DocumentList } from './components/DocumentList'
import { DocumentUpload } from './components/DocumentUpload'
import { DesktopSettings } from './components/DesktopSettings'
import { KnowledgeModeSelector } from './components/KnowledgeModeSelector'
import { LoginForm } from './components/LoginForm'
import { MemoryModeSelector } from './components/MemoryModeSelector'
import { MemorySection } from './components/MemorySection'

type BackendStatus = 'loading' | 'connected' | 'unavailable'

const accessTokenStorageKey = 'personal-ai-assistant.access-token'

function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('loading')
  const [accessToken, setAccessToken] = useState<string | null>(() => getStoredAccessToken())
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [documents, setDocuments] = useState<DocumentResponse[]>([])
  const [memories, setMemories] = useState<MemoryResponse[]>([])
  const [desktopStatus, setDesktopStatus] = useState<DesktopStatusResponse | null>(null)
  const [openAIKeyStatus, setOpenAIKeyStatus] = useState<SecretStatusResponse | null>(null)
  const [knowledgeMode, setKnowledgeMode] = useState<KnowledgeMode>('auto')
  const [memoryMode, setMemoryMode] = useState<MemoryMode>('auto')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [chatError, setChatError] = useState<string | null>(null)
  const [conversationError, setConversationError] = useState<string | null>(null)
  const [documentError, setDocumentError] = useState<string | null>(null)
  const [memoryError, setMemoryError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [desktopSettingsError, setDesktopSettingsError] = useState<string | null>(null)
  const [desktopValidationMessage, setDesktopValidationMessage] = useState<string | null>(null)
  const [liveMessage, setLiveMessage] = useState('')
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [isSendingMessage, setIsSendingMessage] = useState(false)
  const [isLoadingConversations, setIsLoadingConversations] = useState(false)
  const [isLoadingConversation, setIsLoadingConversation] = useState(false)
  const [isDeletingConversation, setIsDeletingConversation] = useState(false)
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false)
  const [isLoadingMemories, setIsLoadingMemories] = useState(false)
  const [isUploadingDocument, setIsUploadingDocument] = useState(false)
  const [isCreatingMemory, setIsCreatingMemory] = useState(false)
  const [isDeletingMemory, setIsDeletingMemory] = useState(false)
  const [isSavingDesktopSettings, setIsSavingDesktopSettings] = useState(false)
  const isSendingMessageRef = useRef(false)
  const chatInputRef = useRef<ChatInputHandle>(null)
  const newChatButtonRef = useRef<HTMLButtonElement | null>(null)
  const conversationButtonRefs = useRef(new Map<string, HTMLButtonElement>())
  const memoryButtonRefs = useRef(new Map<number, HTMLButtonElement>())

  function announce(message: string) {
    setLiveMessage('')
    window.setTimeout(() => setLiveMessage(message), 20)
  }

  useEffect(() => {
    let isMounted = true

    getHealth()
      .then(() => {
        if (isMounted) {
          setBackendStatus('connected')
          announce('Backend connected.')
        }
      })
      .catch(() => {
        if (isMounted) {
          setBackendStatus('unavailable')
          announce('Backend unavailable.')
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    let isMounted = true

    getDesktopStatus()
      .then(async (status) => {
        if (!isMounted) {
          return
        }
        setDesktopStatus(status)
        const secretStatus = await getOpenAIKeyStatus()
        if (isMounted) {
          setOpenAIKeyStatus(secretStatus)
        }
      })
      .catch(() => {
        if (isMounted) {
          setDesktopStatus(null)
          setOpenAIKeyStatus(null)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    if (!accessToken) {
      return
    }

    void Promise.all([
      loadConversations(accessToken),
      loadDocuments(accessToken),
      loadMemories(accessToken),
    ])
  }, [accessToken])

  function clearSession() {
    clearStoredAccessToken()
    isSendingMessageRef.current = false
    setAccessToken(null)
    setConversationId(null)
    setMessages([])
    setConversations([])
    setDocuments([])
    setMemories([])
    setKnowledgeMode('auto')
    setMemoryMode('auto')
    setLoginError(null)
    setChatError(null)
    setConversationError(null)
    setDocumentError(null)
    setMemoryError(null)
    setUploadError(null)
    setIsSendingMessage(false)
    setIsLoadingConversations(false)
    setIsLoadingConversation(false)
    setIsDeletingConversation(false)
    setIsLoadingDocuments(false)
    setIsLoadingMemories(false)
    setIsUploadingDocument(false)
    setIsCreatingMemory(false)
    setIsDeletingMemory(false)
    setLiveMessage('')
  }

  async function handleLogin(email: string, password: string) {
    setIsLoggingIn(true)
    setLoginError(null)

    try {
      const tokenResponse = await login({ email, password })
      storeAccessToken(tokenResponse.access_token)
      setAccessToken(tokenResponse.access_token)
      announce('Signed in.')
      setConversationId(null)
      setMessages([])
      setChatError(null)
      setConversationError(null)
      setDocumentError(null)
      setMemoryError(null)
      setUploadError(null)
    } catch (error) {
      setLoginError(getLoginErrorText(error))
      announce('Sign in failed.')
    } finally {
      setIsLoggingIn(false)
    }
  }

  async function handleRegister(email: string, password: string) {
    setIsLoggingIn(true)
    setLoginError(null)

    try {
      await register({ email, name: email, password })
      const tokenResponse = await login({ email, password })
      storeAccessToken(tokenResponse.access_token)
      setAccessToken(tokenResponse.access_token)
      announce('Account created and signed in.')
      setConversationId(null)
      setMessages([])
      setChatError(null)
      setConversationError(null)
      setDocumentError(null)
      setMemoryError(null)
      setUploadError(null)
    } catch (error) {
      setLoginError(getRegisterErrorText(error))
      announce('Account creation failed.')
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
    announce('Your session expired. Sign in again.')
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

  async function loadConversations(token: string) {
    setIsLoadingConversations(true)
    setConversationError(null)

    try {
      const conversationResponse = await listConversations(token)
      setConversations(conversationResponse)
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setConversationError(getConversationErrorText(error))
    } finally {
      setIsLoadingConversations(false)
    }
  }

  async function handleSelectConversation(selectedConversationId: string) {
    if (!accessToken || isLoadingConversation || selectedConversationId === conversationId) {
      return
    }

    setIsLoadingConversation(true)
    setConversationError(null)
    setChatError(null)

    try {
      const conversation = await getConversation(selectedConversationId, accessToken)
      setConversationId(conversation.conversation_id)
      setMessages(
        conversation.messages
          .filter((message) => message.role === 'user' || message.role === 'assistant')
          .map((message) => ({
            role: message.role,
            content: message.content,
            created_at: message.created_at,
          })),
      )
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setConversationError(getConversationErrorText(error))
    } finally {
      setIsLoadingConversation(false)
    }
  }

  async function handleDeleteConversation(deletedConversationId: string) {
    if (!accessToken || isDeletingConversation) {
      return
    }

    const deletedIndex = conversations.findIndex(
      (conversation) => conversation.conversation_id === deletedConversationId,
    )
    const deletedConversation = conversations[deletedIndex]
    const deletedLabel = deletedConversation ? getConversationLabel(deletedConversation) : 'conversation'

    if (!window.confirm(`Delete conversation: ${deletedLabel}?`)) {
      return
    }

    setIsDeletingConversation(true)
    setConversationError(null)

    try {
      await deleteConversation(deletedConversationId, accessToken)
      setConversations((currentConversations) =>
        currentConversations.filter(
          (conversation) => conversation.conversation_id !== deletedConversationId,
        ),
      )

      if (deletedConversationId === conversationId) {
        handleNewChat()
      }
      announce(`Conversation deleted: ${deletedLabel}.`)
      const nextConversation = conversations[deletedIndex + 1] ?? conversations[deletedIndex - 1]
      window.setTimeout(() => {
        if (nextConversation) {
          conversationButtonRefs.current.get(nextConversation.conversation_id)?.focus()
          return
        }

        newChatButtonRef.current?.focus()
      }, 0)
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setConversationError(getConversationErrorText(error))
    } finally {
      setIsDeletingConversation(false)
    }
  }

  function handleNewChat() {
    setConversationId(null)
    setMessages([])
    setChatError(null)
    announce('New chat ready.')
    window.setTimeout(() => chatInputRef.current?.focus(), 0)
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
        announce('Document uploaded, but processing failed.')
      } else {
        announce(`Document uploaded: ${uploadedDocument.original_filename}.`)
      }
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setUploadError(getDocumentErrorText(error))
      announce('Document upload failed.')
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
      announce(`Memory saved: ${category} / ${key}.`)
      return true
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return false
      }

      setMemoryError(getMemoryErrorText(error))
      announce('Memory save failed.')
      return false
    } finally {
      setIsCreatingMemory(false)
    }
  }

  async function handleDeleteMemory(memoryId: number) {
    if (!accessToken || isDeletingMemory) {
      return
    }

    const deletedIndex = memories.findIndex((memory) => memory.id === memoryId)
    const deletedMemory = memories[deletedIndex]
    const deletedLabel = deletedMemory ? `${deletedMemory.category} / ${deletedMemory.key}` : 'memory'

    if (!window.confirm(`Delete memory: ${deletedLabel}?`)) {
      return
    }

    setIsDeletingMemory(true)
    setMemoryError(null)

    try {
      await deleteMemory(memoryId, accessToken)
      await loadMemories(accessToken)
      announce(`Memory deleted: ${deletedLabel}.`)
      const nextMemory = memories[deletedIndex + 1] ?? memories[deletedIndex - 1]
      window.setTimeout(() => {
        if (nextMemory) {
          memoryButtonRefs.current.get(nextMemory.id)?.focus()
          return
        }

        document.getElementById('memory-section-title')?.focus()
      }, 0)
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setMemoryError(getMemoryErrorText(error))
      announce('Memory delete failed.')
    } finally {
      setIsDeletingMemory(false)
    }
  }

  async function handleSaveOpenAIKey(apiKey: string): Promise<boolean> {
    setIsSavingDesktopSettings(true)
    setDesktopSettingsError(null)
    setDesktopValidationMessage(null)

    try {
      const status = await saveOpenAIKey(apiKey)
      setOpenAIKeyStatus(status)
      setDesktopValidationMessage('OpenAI API key saved securely.')
      announce('OpenAI API key saved.')
      return true
    } catch (error) {
      setDesktopSettingsError(getDesktopSettingsErrorText(error))
      announce('OpenAI API key save failed.')
      return false
    } finally {
      setIsSavingDesktopSettings(false)
    }
  }

  async function handleRemoveOpenAIKey() {
    setIsSavingDesktopSettings(true)
    setDesktopSettingsError(null)
    setDesktopValidationMessage(null)

    try {
      const status = await removeOpenAIKey()
      setOpenAIKeyStatus(status)
      setDesktopValidationMessage('OpenAI API key removed.')
      announce('OpenAI API key removed.')
    } catch (error) {
      setDesktopSettingsError(getDesktopSettingsErrorText(error))
      announce('OpenAI API key removal failed.')
    } finally {
      setIsSavingDesktopSettings(false)
    }
  }

  async function handleTestOpenAIKey() {
    setIsSavingDesktopSettings(true)
    setDesktopSettingsError(null)
    setDesktopValidationMessage(null)

    try {
      const result = await testOpenAIKey()
      setDesktopValidationMessage(result.message)
      announce(result.valid ? 'OpenAI API key test succeeded.' : 'OpenAI API key test failed.')
    } catch (error) {
      setDesktopSettingsError(getDesktopSettingsErrorText(error))
      announce('OpenAI API key test failed.')
    } finally {
      setIsSavingDesktopSettings(false)
    }
  }

  async function handleSubmitMessage(content: string) {
    if (!accessToken || isSendingMessageRef.current) {
      return
    }

    const activeConversationId = conversationId ?? createConversationId()
    isSendingMessageRef.current = true
    setConversationId(activeConversationId)
    setMessages((currentMessages) => [
      ...currentMessages,
      { role: 'user', content },
    ])
    setChatError(null)
    setIsSendingMessage(true)

    try {
      const chatResponse = await sendChat(
        {
          conversation_id: activeConversationId,
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
      announce('Assistant response ready.')
      if (chatResponse.metadata?.actions?.some(isMemoryChangingAction)) {
        await loadMemories(accessToken)
        announce('Assistant response ready. Memory updated.')
      }
      await loadConversations(accessToken)
    } catch (error) {
      if (isAuthenticationError(error)) {
        handleSessionExpired()
        return
      }

      setChatError(getChatErrorText(error))
      announce('Message send failed.')
    } finally {
      isSendingMessageRef.current = false
      setIsSendingMessage(false)
    }
  }

  return (
    <div className="app-shell">
      {accessToken ? (
        <a className="skip-link" href="#conversation-main">
          Skip to conversation
        </a>
      ) : null}
      <div className="visually-hidden" role="status" aria-live="polite" aria-atomic="true">
        {liveMessage}
      </div>
      <header className="app-header">
        <div>
          <h1>Personal AI Assistant</h1>
          <p>Ask a question or start a conversation.</p>
        </div>
        <div className="app-header__actions">
          <p className={`backend-status backend-status--${backendStatus}`} aria-live="polite">
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

      {desktopStatus ? (
        <DesktopSettings
          desktopStatus={desktopStatus}
          keyStatus={openAIKeyStatus}
          isSaving={isSavingDesktopSettings}
          error={desktopSettingsError}
          validationMessage={desktopValidationMessage}
          onSaveKey={handleSaveOpenAIKey}
          onRemoveKey={handleRemoveOpenAIKey}
          onTestKey={handleTestOpenAIKey}
        />
      ) : null}

      {accessToken ? (
        <div className="workspace-panel">
          <ConversationSidebar
            conversations={conversations}
            activeConversationId={conversationId}
            error={conversationError}
            isLoading={isLoadingConversations}
            isDeleting={isDeletingConversation}
            newChatButtonRef={(node) => {
              newChatButtonRef.current = node
            }}
            conversationButtonRef={(id) => (node) => {
              if (node) {
                conversationButtonRefs.current.set(id, node)
              } else {
                conversationButtonRefs.current.delete(id)
              }
            }}
            onNewChat={handleNewChat}
            onSelect={handleSelectConversation}
            onDelete={handleDeleteConversation}
          />

          <main
            className="chat-panel"
            id="conversation-main"
            aria-labelledby="conversation-title"
            tabIndex={-1}
          >
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
                memoryButtonRef={(id) => (node) => {
                  if (node) {
                    memoryButtonRefs.current.set(id, node)
                  } else {
                    memoryButtonRefs.current.delete(id)
                  }
                }}
                onCreate={handleCreateMemory}
                onDelete={handleDeleteMemory}
              />
              <DocumentList
                documents={documents}
                error={documentError}
                isLoading={isLoadingDocuments}
              />
            </div>

            <section
              className="message-list"
              id="message-list"
              aria-labelledby="conversation-title"
              aria-busy={isSendingMessage || isLoadingConversation}
            >
              <h2 className="visually-hidden" id="conversation-title">
                Conversation
              </h2>
              {isLoadingConversation ? (
                <p className="thinking-state" role="status">
                  Loading conversation...
                </p>
              ) : null}

              {!isLoadingConversation && messages.length === 0 ? (
              <div className="empty-state">
                <h2>Ready when you are.</h2>
                <p>Your messages will appear here after you send them to the assistant.</p>
              </div>
              ) : null}

              {messages.map((message, index) => (
                  <ChatMessage key={`${message.role}-${index}`} message={message} />
                ))}

              {isSendingMessage ? (
                <p className="thinking-state" aria-live="polite">
                  Assistant is thinking...
                </p>
              ) : null}
            </section>

            {chatError ? (
              <p className="chat-error" id="chat-error" role="alert">
                {chatError}
              </p>
            ) : null}

            <ChatInput
              ref={chatInputRef}
              onSubmit={handleSubmitMessage}
              disabled={isSendingMessage || isLoadingConversation}
            />
          </main>
        </div>
      ) : (
        <LoginForm
          error={loginError}
          isSubmitting={isLoggingIn}
          onClearError={() => setLoginError(null)}
          onRegister={handleRegister}
          onSubmit={handleLogin}
        />
      )}
    </div>
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

function getRegisterErrorText(error: unknown): string {
  if (isNetworkError(error)) {
    return 'Cannot reach the backend. Try again shortly.'
  }

  if (error instanceof ApiError && error.status === 409) {
    return 'An account with that email already exists.'
  }

  if (error instanceof ApiError && error.status === 422) {
    return 'Check your email and password, then try again.'
  }

  if (error instanceof ApiError) {
    return 'Unable to create account. Try again.'
  }

  return 'Unable to create account. Try again.'
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

function getConversationErrorText(error: unknown): string {
  if (isNetworkError(error)) {
    return 'Cannot reach the backend. Conversation history is unavailable.'
  }

  if (error instanceof ApiError) {
    return error.message
  }

  return 'Unable to update conversation history.'
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

function getDesktopSettingsErrorText(error: unknown): string {
  if (isNetworkError(error)) {
    return 'Cannot reach the local backend. Try again shortly.'
  }

  if (error instanceof ApiError) {
    return error.message
  }

  return 'Unable to update desktop settings.'
}

function isAuthenticationError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

function isNetworkError(error: unknown): boolean {
  return error instanceof TypeError
}

function isMemoryChangingAction(action: { tool_name: string; status: string }): boolean {
  return (
    action.status === 'success' &&
    (action.tool_name === 'save_memory' || action.tool_name === 'delete_memory')
  )
}

function getStoredAccessToken(): string | null {
  try {
    return window.localStorage.getItem(accessTokenStorageKey)
  } catch {
    return null
  }
}

function storeAccessToken(token: string) {
  try {
    window.localStorage.setItem(accessTokenStorageKey, token)
  } catch {
    // If storage is unavailable, the in-memory session still works.
  }
}

function clearStoredAccessToken() {
  try {
    window.localStorage.removeItem(accessTokenStorageKey)
  } catch {
    // Ignore storage failures during logout/session cleanup.
  }
}

export default App
