import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { GreenButton } from '@silent-voice/web-ui/Button'
import { Input } from '@silent-voice/web-ui/Input'
import { authAction, authClient } from './auth-client'
import { useAuthTask } from './use-auth-task'
import '../admin/login.css'
import './security.css'

export function AccountPages() {
  const location = useLocation()
  const query = new URLSearchParams(location.search)
  const token = query.get('token') ?? ''
  const app = query.get('destino') === 'app'
  const verified = location.pathname === '/conta/email-confirmado'
  const reset = location.pathname === '/conta/redefinir-senha'
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [done, setDone] = useState(false)
  const task = useAuthTask()
  const validLink = !query.has('error') && (verified || (reset && !!token))
  const title = !validLink
    ? 'Link inválido ou expirado'
    : verified
      ? 'E-mail confirmado'
      : done
        ? 'Senha redefinida'
        : 'Redefinir senha'
  const handoff = verified
    ? 'silentvoicemobile://auth/email-confirmed'
    : `silentvoicemobile://auth/reset-password?token=${encodeURIComponent(token)}`
  return (
    <main className="admin-login">
      <div className="admin-login-content">
        <section className="admin-login-form" aria-labelledby="account-title">
          <h1 id="account-title" className="admin-login-title">
            {title}
          </h1>
          {!validLink ? (
            <>
              <p className="admin-login-feedback" role="alert">
                Solicite um novo link na tela de acesso.
              </p>
              <Link className="auth-text-button" to="/admin/login">
                Voltar para entrar
              </Link>
            </>
          ) : (
            <>
              {verified && (
                <p className="admin-login-feedback" role="status">
                  Seu e-mail foi confirmado. Você já pode voltar para entrar na
                  sua conta.
                </p>
              )}
              {done && (
                <p className="admin-login-feedback" role="status">
                  Sua senha foi alterada e as sessões anteriores foram
                  encerradas. Entre novamente para continuar.
                </p>
              )}
              {app && !done && (
                <p>
                  <a className="auth-text-button" href={handoff}>
                    Continuar no aplicativo Silent Voice
                  </a>
                </p>
              )}
              {reset && !done && (
                <form
                  aria-busy={task.pending}
                  onSubmit={(event) => {
                    event.preventDefault()
                    if (password !== confirm) {
                      task.setError('As senhas precisam ser iguais.')
                      return
                    }
                    void task.run(async (signal) => {
                      try {
                        await authAction(
                          () =>
                            authClient.resetPassword({
                              token,
                              newPassword: password,
                              fetchOptions: { signal },
                            }),
                          signal
                        )
                        setDone(true)
                        window.history.replaceState(null, '', location.pathname)
                      } finally {
                        setPassword('')
                        setConfirm('')
                      }
                    })
                  }}
                >
                  <label className="admin-login-field">
                    Nova senha
                    <Input
                      type="password"
                      autoComplete="new-password"
                      minLength={12}
                      maxLength={128}
                      required
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      disabled={task.pending}
                    />
                  </label>
                  <label className="admin-login-field">
                    Confirmar nova senha
                    <Input
                      type="password"
                      autoComplete="new-password"
                      minLength={12}
                      maxLength={128}
                      required
                      value={confirm}
                      onChange={(event) => setConfirm(event.target.value)}
                      disabled={task.pending}
                    />
                  </label>
                  <p className="admin-login-feedback">
                    Use uma senha com 12 a 128 caracteres.
                  </p>
                  {task.error && (
                    <p
                      ref={task.errorRef}
                      tabIndex={-1}
                      className="admin-login-feedback"
                      role="alert"
                    >
                      {task.error}
                    </p>
                  )}
                  <GreenButton type="submit" disabled={task.pending}>
                    {task.pending ? 'Aguarde…' : 'Salvar nova senha'}
                  </GreenButton>
                </form>
              )}
              {(verified || done) && (
                <Link className="auth-text-button" to="/admin/login">
                  Voltar para entrar
                </Link>
              )}
            </>
          )}
        </section>
      </div>
    </main>
  )
}
