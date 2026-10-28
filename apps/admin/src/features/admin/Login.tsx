import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import * as m from 'motion/react-m'
import { useSectionEntrance } from '@silent-voice/web-ui/entrance'
import { GreenButton } from '@silent-voice/web-ui/Button'
import { Input } from '@silent-voice/web-ui/Input'
import {
  AuthError,
  authAction,
  authClient,
  getAuthSession,
} from '../auth/auth-client'
import type { AuthSession } from '../auth/auth-client'
import './login.css'

export function Login({
  onLogin,
  expired,
}: {
  onLogin: (session: AuthSession) => void
  expired: boolean
}) {
  const { ref, enter, revealOnFocus } = useSectionEntrance<HTMLElement>()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState<
    'login' | 'totp' | 'backup' | 'forgot' | 'verify'
  >('login')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [invalidCredentials, setInvalidCredentials] = useState(false)
  const controller = useRef<AbortController | null>(null)
  const passwordInput = useRef<HTMLInputElement>(null)
  const codeInput = useRef<HTMLInputElement>(null)
  const feedback = useRef<HTMLParagraphElement>(null)
  useEffect(() => () => controller.current?.abort(), [])
  useEffect(() => {
    if (error && !pending)
      (step === 'login'
        ? passwordInput.current
        : step === 'totp' || step === 'backup'
          ? codeInput.current
          : feedback.current
      )?.focus()
  }, [error, pending, step])
  useEffect(() => {
    if (step === 'totp' || step === 'backup') codeInput.current?.focus()
  }, [step])
  function changeStep(value: typeof step) {
    setStep(value)
    setError('')
    setNotice('')
    setCode('')
    setPassword('')
    setInvalidCredentials(false)
  }
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (pending) return
    const active = new AbortController()
    controller.current = active
    setPending(true)
    setError('')
    setNotice('')
    setInvalidCredentials(false)
    const options = { signal: active.signal }
    try {
      if (step === 'forgot') {
        await authAction(
          () =>
            authClient.requestPasswordReset({
              email: email.trim(),
              redirectTo: `${window.location.origin}/conta/redefinir-senha`,
              fetchOptions: options,
            }),
          active.signal
        )
        setNotice(
          'Se houver uma conta com este e-mail, você receberá um link para redefinir sua senha.'
        )
      } else if (step === 'verify') {
        await authAction(
          () =>
            authClient.sendVerificationEmail({
              email: email.trim(),
              callbackURL: `${window.location.origin}/conta/email-confirmado`,
              fetchOptions: options,
            }),
          active.signal
        )
        setNotice(
          'Solicitação concluída. Confira sua caixa de entrada e o spam para confirmar o e-mail.'
        )
      } else {
        const result =
          step === 'login'
            ? await authAction(
                () =>
                  authClient.signIn.email({
                    email: email.trim(),
                    password,
                    fetchOptions: options,
                  }),
                active.signal
              )
            : step === 'totp'
              ? await authAction(
                  () =>
                    authClient.twoFactor.verifyTotp({
                      code: code.trim(),
                      trustDevice: false,
                      fetchOptions: options,
                    }),
                  active.signal
                )
              : await authAction(
                  () =>
                    authClient.twoFactor.verifyBackupCode({
                      code: code.trim(),
                      trustDevice: false,
                      fetchOptions: options,
                    }),
                  active.signal
                )
        setPassword('')
        setCode('')
        if (
          result &&
          'twoFactorRedirect' in result &&
          result.twoFactorRedirect
        ) {
          setStep('totp')
          return
        }
        const session = await getAuthSession(active.signal)
        if (!session) throw new AuthError('SESSION_REQUIRED')
        active.signal.throwIfAborted()
        onLogin(session)
      }
    } catch (cause) {
      if (active.signal.aborted) return
      setPassword('')
      setCode('')
      if (cause instanceof AuthError && cause.code === 'EMAIL_NOT_VERIFIED')
        setStep('verify')
      setInvalidCredentials(
        step === 'login' &&
          cause instanceof AuthError &&
          (cause.status === 401 || cause.code === 'INVALID_EMAIL_OR_PASSWORD')
      )
      setError(
        cause instanceof AuthError
          ? cause.message
          : 'Não foi possível concluir. Verifique sua conexão e tente novamente.'
      )
    } finally {
      if (!active.signal.aborted) setPending(false)
    }
  }
  const title =
    step === 'forgot'
      ? 'Recuperar acesso'
      : step === 'verify'
        ? 'Confirme seu e-mail'
        : step === 'totp' || step === 'backup'
          ? 'Verificação em duas etapas'
          : 'Entrar'
  return (
    <main className="admin-login">
      <div className="admin-login-content">
        <m.section
          ref={ref}
          className="admin-login-form entrance-control"
          aria-labelledby="admin-login-title"
          onFocusCapture={revealOnFocus}
          {...enter(0, 12, 0.55)}
        >
          <m.h1
            id="admin-login-title"
            className="admin-login-title"
            {...enter(0.08, 8, 0.5)}
          >
            {title}
          </m.h1>
          {expired && (
            <p className="admin-login-feedback" role="status">
              Sua sessão expirou. Entre novamente para continuar. Seus rascunhos
              foram preservados nesta janela.
            </p>
          )}
          <form onSubmit={submit} aria-busy={pending}>
            {(step === 'login' || step === 'forgot' || step === 'verify') && (
              <m.label className="admin-login-field" {...enter(0.16, 10, 0.5)}>
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
              </m.label>
            )}
            {step === 'login' && (
              <m.label className="admin-login-field" {...enter(0.24, 10, 0.5)}>
                <span>Senha</span>
                <Input
                  ref={passwordInput}
                  type="password"
                  maxLength={128}
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
              </m.label>
            )}
            {(step === 'totp' || step === 'backup') && (
              <label className="admin-login-field">
                <span>
                  {step === 'totp'
                    ? 'Código do autenticador'
                    : 'Código de recuperação'}
                </span>
                <Input
                  ref={codeInput}
                  autoComplete="one-time-code"
                  inputMode={step === 'totp' ? 'numeric' : 'text'}
                  pattern={step === 'totp' ? '[0-9]{6}' : undefined}
                  maxLength={step === 'totp' ? 6 : 100}
                  required
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  disabled={pending}
                  aria-describedby={error ? 'admin-login-error' : undefined}
                />
              </label>
            )}
            {error && (
              <p
                ref={feedback}
                tabIndex={-1}
                className="admin-login-feedback"
                id="admin-login-error"
                role="alert"
              >
                {error}
              </p>
            )}
            {notice && (
              <p className="admin-login-feedback" role="status">
                {notice}
              </p>
            )}
            <m.div {...enter(0.32, 8, 0.5)}>
              <GreenButton type="submit" disabled={pending}>
                {pending
                  ? 'Aguarde…'
                  : step === 'login'
                    ? 'Entrar'
                    : step === 'forgot'
                      ? 'Enviar link de recuperação'
                      : step === 'verify'
                        ? 'Reenviar confirmação'
                        : 'Verificar código'}
              </GreenButton>
            </m.div>
            {step === 'login' && (
              <button
                className="auth-text-button"
                type="button"
                disabled={pending}
                onClick={() => changeStep('forgot')}
              >
                Esqueci minha senha
              </button>
            )}
            {(step === 'totp' || step === 'backup') && (
              <button
                className="auth-text-button"
                type="button"
                disabled={pending}
                onClick={() => changeStep(step === 'totp' ? 'backup' : 'totp')}
              >
                {step === 'totp'
                  ? 'Usar código de recuperação'
                  : 'Usar autenticador'}
              </button>
            )}
            {step !== 'login' && (
              <button
                className="auth-text-button"
                type="button"
                disabled={pending}
                onClick={() => changeStep('login')}
              >
                Voltar para entrar
              </button>
            )}
          </form>
        </m.section>
      </div>
    </main>
  )
}
