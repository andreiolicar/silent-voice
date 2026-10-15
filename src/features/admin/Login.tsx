import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { GreenButton } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { AdminApiError, adminFetch, apiMessage, isAborted } from './admin-api'
import type { Session } from './admin-api'
import './login.css'

export function Login({
  onLogin,
  expired,
}: {
  onLogin: (session: Session) => void
  expired: boolean
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [invalidCredentials, setInvalidCredentials] = useState(false)
  const controller = useRef<AbortController | null>(null)
  const passwordInput = useRef<HTMLInputElement>(null)
  useEffect(() => () => controller.current?.abort(), [])
  useEffect(() => {
    if (error && !pending) passwordInput.current?.focus()
  }, [error, pending])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (pending) return
    setPending(true)
    setError('')
    setInvalidCredentials(false)
    controller.current?.abort()
    controller.current = new AbortController()
    const signal = controller.current.signal
    try {
      const { csrfToken } = await adminFetch<{ csrfToken: string }>(
        '/auth/csrf',
        { signal }
      )
      const result = await adminFetch<Session>(
        '/auth/login',
        {
          method: 'POST',
          signal,
          body: JSON.stringify({ email: email.trim(), password }),
        },
        csrfToken
      )
      setPassword('')
      onLogin(result)
    } catch (error) {
      if (isAborted(error)) return
      setPassword('')
      const invalid = error instanceof AdminApiError && error.status === 401
      setInvalidCredentials(invalid)
      setError(
        invalid
          ? 'E-mail ou senha incorretos. Tente novamente.'
          : apiMessage(error)
      )
    } finally {
      if (!signal.aborted) setPending(false)
    }
  }

  return (
    <main className="admin-login">
      <div className="admin-login-content">
        <section
          className="admin-login-form"
          aria-labelledby="admin-login-title"
        >
          <h1 id="admin-login-title" className="admin-login-title">
            Entrar
          </h1>
          {expired && (
            <p className="admin-login-feedback" role="status">
              Sua sessão expirou. Entre novamente para continuar. Seus rascunhos
              foram preservados nesta janela.
            </p>
          )}
          <form onSubmit={submit} aria-busy={pending}>
            <label className="admin-login-field">
              <span>E-mail</span>
              <Input
                type="email"
                maxLength={254}
                autoComplete="username"
                placeholder="seu@email.com"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={pending}
              />
            </label>
            <label className="admin-login-field">
              <span>Senha</span>
              <Input
                ref={passwordInput}
                type="password"
                maxLength={256}
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value)
                  if (invalidCredentials) {
                    setInvalidCredentials(false)
                    setError('')
                  }
                }}
                disabled={pending}
                aria-invalid={invalidCredentials || undefined}
                aria-describedby={error ? 'admin-login-error' : undefined}
              />
            </label>
            {error && (
              <p
                className="admin-login-feedback"
                id="admin-login-error"
                role="alert"
              >
                {error}
              </p>
            )}
            <GreenButton type="submit" disabled={pending}>
              {pending ? 'Entrando…' : 'Entrar'}
            </GreenButton>
          </form>
        </section>
      </div>
    </main>
  )
}
