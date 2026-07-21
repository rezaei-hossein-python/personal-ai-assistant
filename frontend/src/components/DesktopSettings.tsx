import { useId, useRef, useState, type FormEvent } from 'react'
import type { DesktopStatusResponse, SecretStatusResponse } from '../api/types'

interface DesktopSettingsProps {
  desktopStatus: DesktopStatusResponse
  keyStatus: SecretStatusResponse | null
  isSaving: boolean
  error: string | null
  validationMessage: string | null
  onSaveKey: (apiKey: string) => Promise<boolean>
  onRemoveKey: () => void
  onTestKey: () => void
}

export function DesktopSettings({
  desktopStatus,
  keyStatus,
  isSaving,
  error,
  validationMessage,
  onSaveKey,
  onRemoveKey,
  onTestKey,
}: DesktopSettingsProps) {
  const [apiKey, setApiKey] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const errorId = useId()
  const helpId = useId()
  const statusId = useId()
  const lastActionRef = useRef<HTMLButtonElement | null>(null)
  const isSubmitDisabled = isSaving || apiKey.trim().length === 0
  const fieldError = validationError ?? error
  const keyStatusText = keyStatus?.configured ? 'OpenAI API key: configured' : 'OpenAI API key: not configured'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitDisabled) {
      return
    }

    if (!apiKey.trim().startsWith('sk-')) {
      setValidationError('Enter a valid OpenAI API key beginning with sk-.')
      return
    }

    setValidationError(null)
    const saved = await onSaveKey(apiKey.trim())
    if (saved) {
      setApiKey('')
    }
    window.setTimeout(() => lastActionRef.current?.focus(), 0)
  }

  function handleTest() {
    onTestKey()
    window.setTimeout(() => lastActionRef.current?.focus(), 0)
  }

  function handleRemove() {
    if (!window.confirm('Remove the saved OpenAI API key?')) {
      window.setTimeout(() => lastActionRef.current?.focus(), 0)
      return
    }

    onRemoveKey()
    window.setTimeout(() => lastActionRef.current?.focus(), 0)
  }

  return (
    <section className="desktop-settings" aria-labelledby="desktop-settings-title">
      <div className="desktop-settings__summary">
        <h2 id="desktop-settings-title">Desktop settings</h2>
        {!keyStatus?.configured ? (
          <p>
            An OpenAI API key is required for AI responses. It is stored with the
            operating system credential store.
          </p>
        ) : null}
        <dl>
          <div>
            <dt>OpenAI key</dt>
            <dd>
              <span id={statusId}>{keyStatusText}</span>
              {keyStatus?.configured && keyStatus.masked ? (
                <span aria-hidden="true"> ({keyStatus.masked})</span>
              ) : null}
            </dd>
          </div>
          <div>
            <dt>Data directory</dt>
            <dd>{desktopStatus.data_directory}</dd>
          </div>
          <div>
            <dt>Logs</dt>
            <dd>{desktopStatus.logs_directory}</dd>
          </div>
          <div>
            <dt>Database</dt>
            <dd>{desktopStatus.database_backend}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>{desktopStatus.app_version}</dd>
          </div>
        </dl>
      </div>

      <form className="desktop-settings__key-form" onSubmit={handleSubmit} aria-busy={isSaving}>
        <label htmlFor="desktop-openai-key">OpenAI API key</label>
        <p id={helpId} className="desktop-settings__field-help">
          Paste a key to save it. Saved keys are stored in the operating system credential store.
        </p>
        <div>
          <input
            id="desktop-openai-key"
            type="password"
            value={apiKey}
            onChange={(event) => {
              setApiKey(event.target.value)
              setValidationError(null)
            }}
            autoComplete="off"
            disabled={isSaving}
            aria-describedby={`${helpId} ${statusId}${fieldError ? ` ${errorId}` : ''}`}
            aria-invalid={fieldError ? true : undefined}
          />
          <button
            type="submit"
            disabled={isSubmitDisabled}
            ref={(node) => {
              if (node) {
                lastActionRef.current = node
              }
            }}
          >
            {isSaving ? 'Saving...' : 'Save key'}
          </button>
          <button
            type="button"
            onClick={handleTest}
            disabled={isSaving}
            ref={(node) => {
              if (node) {
                lastActionRef.current = node
              }
            }}
          >
            Test key
          </button>
          <button
            className="button-danger"
            type="button"
            onClick={handleRemove}
            disabled={isSaving || !keyStatus?.configured}
            ref={(node) => {
              if (node) {
                lastActionRef.current = node
              }
            }}
          >
            Remove key
          </button>
        </div>
      </form>

      {validationMessage ? (
        <p className="desktop-settings__message" role="status">
          {validationMessage}
        </p>
      ) : null}
      {fieldError ? (
        <p className="form-error" id={errorId} role="alert">
          {fieldError}
        </p>
      ) : null}
    </section>
  )
}
