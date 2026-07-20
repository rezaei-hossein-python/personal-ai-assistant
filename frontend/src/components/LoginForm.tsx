import { useState, type FormEvent } from 'react'

interface LoginFormProps {
  error: string | null
  isSubmitting: boolean
  onSubmit: (email: string, password: string) => void
}

export function LoginForm({ error, isSubmitting, onSubmit }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const isSubmitDisabled = isSubmitting || email.trim().length === 0 || password.length === 0

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (isSubmitDisabled) {
      return
    }

    onSubmit(email.trim(), password)
  }

  return (
    <section className="login-panel" aria-labelledby="login-title">
      <form className="login-form" onSubmit={handleSubmit}>
        <div>
          <h2 id="login-title">Sign in</h2>
          <p>Use your assistant account to start chatting.</p>
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
            autoComplete="current-password"
            disabled={isSubmitting}
            required
          />
        </div>

        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}

        <button className="login-form__button" type="submit" disabled={isSubmitDisabled}>
          {isSubmitting ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </section>
  )
}
