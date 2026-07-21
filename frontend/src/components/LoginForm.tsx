import { useState, type FormEvent } from 'react'

interface LoginFormProps {
  error: string | null
  isSubmitting: boolean
  onClearError: () => void
  onRegister: (email: string, password: string) => void
  onSubmit: (email: string, password: string) => void
}

type AuthMode = 'login' | 'register'

export function LoginForm({
  error,
  isSubmitting,
  onClearError,
  onRegister,
  onSubmit,
}: LoginFormProps) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const trimmedEmail = email.trim()
  const isRegistering = mode === 'register'
  const isSubmitDisabled =
    isSubmitting ||
    trimmedEmail.length === 0 ||
    password.length === 0 ||
    (isRegistering && confirmPassword.length === 0)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (isSubmitDisabled) {
      return
    }

    if (!isValidEmail(trimmedEmail)) {
      setValidationError('Enter a valid email address.')
      return
    }

    if (isRegistering && password !== confirmPassword) {
      setValidationError('Passwords do not match.')
      return
    }

    setValidationError(null)

    if (isRegistering) {
      onRegister(trimmedEmail, password)
      return
    }

    onSubmit(trimmedEmail, password)
  }

  function handleModeChange(nextMode: AuthMode) {
    setMode(nextMode)
    setValidationError(null)
    setConfirmPassword('')
    onClearError()
  }

  return (
    <section className="login-panel" aria-labelledby="login-title">
      <form className="login-form" onSubmit={handleSubmit}>
        <div>
          <h2 id="login-title">{isRegistering ? 'Create account' : 'Sign in'}</h2>
          <p>
            {isRegistering
              ? 'Create your assistant account to start chatting.'
              : 'Use your assistant account to start chatting.'}
          </p>
        </div>

        <div className="login-form__field">
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            disabled={isSubmitting}
            required
          />
        </div>

        <div className="login-form__field">
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={isRegistering ? 'new-password' : 'current-password'}
            disabled={isSubmitting}
            required
          />
        </div>

        {isRegistering ? (
          <div className="login-form__field">
            <label htmlFor="login-confirm-password">Confirm password</label>
            <input
              id="login-confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              autoComplete="new-password"
              disabled={isSubmitting}
              required
            />
          </div>
        ) : null}

        {validationError || error ? (
          <p className="form-error" role="alert">
            {validationError ?? error}
          </p>
        ) : null}

        <button className="login-form__button" type="submit" disabled={isSubmitDisabled}>
          {getSubmitText(isSubmitting, isRegistering)}
        </button>

        <button
          className="login-form__secondary-button"
          type="button"
          onClick={() => handleModeChange(isRegistering ? 'login' : 'register')}
          disabled={isSubmitting}
        >
          {isRegistering ? 'Sign in instead' : 'Create account'}
        </button>
      </form>
    </section>
  )
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function getSubmitText(isSubmitting: boolean, isRegistering: boolean): string {
  if (isSubmitting) {
    return isRegistering ? 'Creating account...' : 'Signing in...'
  }

  return isRegistering ? 'Create account' : 'Sign in'
}
