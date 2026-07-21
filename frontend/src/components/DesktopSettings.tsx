import { useState, type FormEvent } from 'react'
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
  const isSubmitDisabled = isSaving || apiKey.trim().length === 0

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitDisabled) {
      return
    }

    const saved = await onSaveKey(apiKey.trim())
    if (saved) {
      setApiKey('')
    }
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
            <dd>{keyStatus?.configured ? keyStatus.masked ?? 'Configured' : 'Not configured'}</dd>
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

      <form className="desktop-settings__key-form" onSubmit={handleSubmit}>
        <label htmlFor="desktop-openai-key">OpenAI API key</label>
        <div>
          <input
            id="desktop-openai-key"
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            autoComplete="off"
            disabled={isSaving}
          />
          <button type="submit" disabled={isSubmitDisabled}>
            {isSaving ? 'Saving...' : 'Save key'}
          </button>
          <button type="button" onClick={onTestKey} disabled={isSaving}>
            Test
          </button>
          <button type="button" onClick={onRemoveKey} disabled={isSaving || !keyStatus?.configured}>
            Remove
          </button>
        </div>
      </form>

      {validationMessage ? <p className="desktop-settings__message">{validationMessage}</p> : null}
      {error ? <p className="form-error" role="alert">{error}</p> : null}
    </section>
  )
}
