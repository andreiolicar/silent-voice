import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import QRCode from 'react-qr-code'
import {
  AuthError,
  authAction,
  authClient,
  getAuthSession,
} from './auth-client'
import type { AuthSession } from './auth-client'
import { useAuthTask } from './use-auth-task'
import { AdminButton } from '../admin/AdminButton'
import { Input } from '@silent-voice/web-ui/Input'
import './security.css'

type ListedSession = {
  id: string
  token: string
  userAgent?: string | null
  ipAddress?: string | null
  expiresAt: string | Date
}
export function SecurityPage({
  session,
  onReauthenticate,
  onLogout,
  onSessionRevoked,
  onSessionChanged,
}: {
  session: AuthSession
  onReauthenticate: () => void
  onLogout: () => void
  onSessionRevoked: () => void
  onSessionChanged: (session: AuthSession) => void
}) {
  const task = useAuthTask(onReauthenticate)
  const [password, setPassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [code, setCode] = useState('')
  const [enrollment, setEnrollment] = useState<{
    uri: string
    codes: string[]
  } | null>(null)
  const [saved, setSaved] = useState(false)
  const [reconfigure, setReconfigure] = useState(false)
  const [completed, setCompleted] = useState('')
  const [notice, setNotice] = useState('')
  const [sessions, setSessions] = useState<ListedSession[]>([])
  const [listPending, setListPending] = useState(true)
  const [listError, setListError] = useState('')
  const [listVersion, setListVersion] = useState(0)
  useEffect(() => {
    const active = new AbortController()
    setListError('')
    setListPending(true)
    authAction(
      () =>
        authClient.listSessions({ fetchOptions: { signal: active.signal } }),
      active.signal
    )
      .then((result) => {
        if (!active.signal.aborted) setSessions(result)
      })
      .catch((cause) => {
        if (active.signal.aborted) return
        if (cause instanceof AuthError && cause.status === 401)
          onReauthenticate()
        else setListError('Não foi possível carregar as sessões.')
      })
      .finally(() => {
        if (!active.signal.aborted) setListPending(false)
      })
    return () => active.abort()
  }, [listVersion, onReauthenticate])
  const secret = enrollment
    ? (new URL(enrollment.uri).searchParams.get('secret') ?? '')
    : ''
  function setup(event: FormEvent) {
    event.preventDefault()
    void task.run(async (signal) => {
      try {
        const result = await authAction(
          () =>
            authClient.twoFactor.enable({
              password,
              method: 'totp',
              fetchOptions: { signal },
            }),
          signal
        )
        if (result.method !== 'totp') throw new Error('totp_required')
        setEnrollment({ uri: result.totpURI, codes: result.backupCodes })
        setSaved(false)
      } finally {
        setPassword('')
      }
    })
  }
  function verify(event: FormEvent) {
    event.preventDefault()
    if (!saved) return
    void task.run(async (signal) => {
      await authAction(
        () =>
          authClient.twoFactor.verifyTotp({
            code: code.trim(),
            trustDevice: false,
            fetchOptions: { signal },
          }),
        signal
      )
      onSessionRevoked()
      setCode('')
      setEnrollment(null)
      setCompleted(
        'Autenticador confirmado. Suas sessões foram encerradas. Entre novamente com a senha e o código do autenticador.'
      )
    })
  }
  function resetAuthenticator(event: FormEvent) {
    event.preventDefault()
    if (!reconfigure) return
    void task.run(async (signal) => {
      try {
        await authAction(
          () =>
            authClient.twoFactor.disable({
              password,
              fetchOptions: { signal },
            }),
          signal
        )
        onSessionRevoked()
        setCompleted(
          'Suas sessões foram encerradas. Entre novamente para configurar o novo autenticador antes de acessar a gestão.'
        )
      } finally {
        setPassword('')
      }
    })
  }
  function changePassword(event: FormEvent) {
    event.preventDefault()
    void task.run(async (signal) => {
      try {
        await authAction(
          () =>
            authClient.changePassword({
              currentPassword,
              newPassword,
              revokeOtherSessions: true,
              fetchOptions: { signal },
            }),
          signal
        )
        // revokeOtherSessions rotates the current session too. Adopt its ID and
        // expiry before offering session controls or retaining the parent timer.
        let current: AuthSession | null
        try {
          current = await getAuthSession(signal)
        } catch {
          signal.throwIfAborted()
          onReauthenticate()
          return
        }
        signal.throwIfAborted()
        if (!current) {
          onReauthenticate()
          return
        }
        setListPending(true)
        onSessionChanged(current)
        setNotice('Senha alterada. As outras sessões foram encerradas.')
        setListVersion((value) => value + 1)
      } finally {
        setCurrentPassword('')
        setNewPassword('')
      }
    })
  }
  if (completed)
    return (
      <section className="auth-security">
        <h1>Segurança da conta</h1>
        <p role="status">{completed}</p>
        <AdminButton onClick={onReauthenticate}>Entrar novamente</AdminButton>
      </section>
    )
  return (
    <section className="auth-security" aria-labelledby="security-title">
      <h1 id="security-title">Segurança da conta</h1>
      <p>{session.user.email}</p>
      {!session.user.twoFactorEnabled && (
        <p className="admin-notice">
          Configure a verificação em duas etapas para acessar a área de gestão.
        </p>
      )}
      {task.error && (
        <p
          className="admin-error"
          tabIndex={-1}
          ref={task.errorRef}
          role="alert"
        >
          {task.error}
        </p>
      )}
      {notice && (
        <p role="status" className="admin-notice">
          {notice}
        </p>
      )}
      <section className="auth-security-card">
        <h2>Autenticador</h2>
        {enrollment ? (
          <>
            <p>
              Escaneie o QR code no seu aplicativo autenticador ou use a chave
              manual.
            </p>
            <div className="auth-qr">
              <QRCode
                value={enrollment.uri}
                size={180}
                title="QR code para configurar o autenticador"
              />
            </div>
            <label className="admin-field">
              Chave manual
              <Input readOnly value={secret} />
            </label>
            <AdminButton
              disabled={task.pending}
              onClick={() => {
                void task.run(async () => {
                  await navigator.clipboard.writeText(secret)
                  setNotice('Chave copiada.')
                })
              }}
            >
              Copiar chave
            </AdminButton>
            <h3>Códigos de recuperação</h3>
            <p>
              Guarde estes códigos em um lugar seguro antes de confirmar. Cada
              código pode ser usado uma vez. Eles deixam de aparecer ao sair
              desta página.
            </p>
            <ul className="auth-backup-codes">
              {enrollment.codes.map((item) => (
                <li key={item}>
                  <code>{item}</code>
                </li>
              ))}
            </ul>
            <label className="auth-checkbox">
              <input
                type="checkbox"
                checked={saved}
                onChange={(event) => setSaved(event.target.checked)}
                disabled={task.pending}
              />{' '}
              Guardei meus códigos de recuperação
            </label>
            <form onSubmit={verify} aria-busy={task.pending}>
              <label className="admin-field">
                Primeiro código do autenticador
                <Input
                  autoFocus
                  required
                  autoComplete="one-time-code"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  disabled={task.pending}
                />
              </label>
              <AdminButton type="submit" disabled={!saved || task.pending}>
                Confirmar autenticador
              </AdminButton>
            </form>
          </>
        ) : !session.user.twoFactorEnabled ? (
          <form onSubmit={setup} aria-busy={task.pending}>
            <p>
              Use um aplicativo autenticador compatível com códigos temporários
              (TOTP).
            </p>
            <label className="admin-field">
              Senha atual
              <Input
                type="password"
                required
                maxLength={128}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={task.pending}
              />
            </label>
            <AdminButton type="submit" disabled={task.pending}>
              Ativar autenticador
            </AdminButton>
          </form>
        ) : (
          <form onSubmit={resetAuthenticator} aria-busy={task.pending}>
            <p>
              O autenticador está ativo. Ao reconfigurar, todas as sessões serão
              encerradas. Você precisará entrar e cadastrar um novo autenticador
              para voltar à gestão.
            </p>
            <label className="admin-field">
              Senha para reconfigurar
              <Input
                type="password"
                autoComplete="current-password"
                maxLength={128}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={task.pending}
              />
            </label>
            <label className="auth-checkbox">
              <input
                type="checkbox"
                checked={reconfigure}
                onChange={(event) => setReconfigure(event.target.checked)}
                disabled={task.pending}
              />{' '}
              Quero substituir meu autenticador e encerrar todas as sessões
            </label>
            <AdminButton type="submit" disabled={!reconfigure || task.pending}>
              Reconfigurar autenticador
            </AdminButton>
          </form>
        )}
      </section>
      {!enrollment && (
        <section className="auth-security-card">
          <h2>Alterar senha</h2>
          <form onSubmit={changePassword} aria-busy={task.pending}>
            <label className="admin-field">
              Senha atual para alterar
              <Input
                type="password"
                required
                autoComplete="current-password"
                maxLength={128}
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                disabled={task.pending}
              />
            </label>
            <label className="admin-field">
              Nova senha
              <Input
                type="password"
                required
                minLength={12}
                maxLength={128}
                autoComplete="new-password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                disabled={task.pending}
              />
            </label>
            <p>
              Use de 12 a 128 caracteres. As outras sessões serão encerradas.
            </p>
            <AdminButton type="submit" disabled={task.pending}>
              Alterar senha
            </AdminButton>
          </form>
        </section>
      )}
      <section className="auth-security-card">
        <h2>Sessões ativas</h2>
        {listPending ? (
          <p role="status">Carregando sessões…</p>
        ) : listError ? (
          <>
            <p role="alert">{listError}</p>
            <AdminButton onClick={() => setListVersion((value) => value + 1)}>
              Tentar novamente
            </AdminButton>
          </>
        ) : (
          <ul className="auth-sessions">
            {sessions.map((item) => (
              <li key={item.id}>
                <div>
                  <strong>
                    {item.id === session.session.id
                      ? 'Esta sessão'
                      : 'Outra sessão'}
                  </strong>
                  <p>{item.userAgent || 'Dispositivo não informado'}</p>
                  <p>
                    Expira em {new Date(item.expiresAt).toLocaleString('pt-BR')}
                  </p>
                </div>
                <AdminButton
                  disabled={task.pending}
                  onClick={() => {
                    if (item.id === session.session.id) onLogout()
                    else
                      void task.run(async (signal) => {
                        await authAction(
                          () =>
                            authClient.revokeSession({
                              token: item.token,
                              fetchOptions: { signal },
                            }),
                          signal
                        )
                        setListVersion((value) => value + 1)
                        setNotice('Sessão encerrada.')
                      })
                  }}
                >
                  {item.id === session.session.id
                    ? 'Sair desta sessão'
                    : 'Encerrar sessão'}
                </AdminButton>
              </li>
            ))}
          </ul>
        )}
        <AdminButton
          disabled={task.pending}
          onClick={() => {
            void task.run(async (signal) => {
              await authAction(
                () =>
                  authClient.revokeOtherSessions({ fetchOptions: { signal } }),
                signal
              )
              setListVersion((value) => value + 1)
              setNotice('Outras sessões encerradas.')
            })
          }}
        >
          Encerrar outras sessões
        </AdminButton>
      </section>
    </section>
  )
}
