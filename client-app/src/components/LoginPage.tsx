import { useState, type FormEvent } from 'react'
import { login } from '../api/endpoints'
import { errorMessage } from '../api/messages'

interface LoginPageProps {
  notice: string | null
  onLoggedIn: (token: string) => void
}

export function LoginPage({ notice, onLoggedIn }: LoginPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const { access_token } = await login(email.trim(), password)
      onLoggedIn(access_token)
    } catch (err) {
      setError(errorMessage(err))
      setSubmitting(false)
    }
  }

  return (
    <main className="shell shell--narrow">
      <form className="card stack" onSubmit={handleSubmit} noValidate>
        <div>
          <h1>Ingresar</h1>
          <p className="muted">Accede para ver y gestionar tus reservas.</p>
        </div>

        {notice && <p className="alert">{notice}</p>}

        <label className="field">
          <span>Email</span>
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>

        <label className="field">
          <span>Contraseña</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error && (
          <p className="alert alert--error" role="alert">
            {error}
          </p>
        )}

        <button
          className="btn btn--primary"
          type="submit"
          disabled={submitting || !email || !password}
        >
          {submitting ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
    </main>
  )
}
