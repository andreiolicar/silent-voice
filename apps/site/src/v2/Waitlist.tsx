import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Typography } from '@silent-voice/web-ui/Typography'
import { Check } from 'lucide-react'
import { z } from 'zod'
import { registerInterest } from './waitlist-client'
export function Waitlist() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<
    'idle' | 'pending' | 'success' | 'error'
  >('idle')
  const [error, setError] = useState('')
  const [invalid, setInvalid] = useState(false)
  const request = useRef<AbortController | null>(null)
  const pending = useRef(false)
  const id = useId()
  useEffect(
    () => () => {
      request.current?.abort()
      request.current = null
    },
    [],
  )
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (pending.current) return
    if (
      !z.string().trim().toLowerCase().max(254).email().safeParse(email).success
    ) {
      setInvalid(true)
      setError('Informe um e-mail válido.')
      return
    }
    setInvalid(false)
    setError('')
    setStatus('pending')
    pending.current = true
    const controller = new AbortController()
    request.current = controller
    const timer = setTimeout(() => controller.abort(), 105_000)
    try {
      await registerInterest(email, controller.signal)
      if (request.current === controller) setStatus('success')
    } catch (cause) {
      if (request.current === controller) {
        setStatus('error')
        if (cause instanceof Error && cause.message === 'invalid_email') {
          setInvalid(true)
          setError('Informe um e-mail válido.')
          return
        }
        setError(
          cause instanceof Error && cause.message === 'rate_limited'
            ? 'Muitas tentativas. Aguarde alguns minutos e tente novamente.'
            : 'Não foi possível confirmar sua inscrição. Tente novamente ou fale com a equipe.',
        )
      }
    } finally {
      clearTimeout(timer)
      pending.current = false
    }
  }
  return (
    <section
      className="v2-waitlist"
      id="lista"
      aria-labelledby="waitlist-title"
    >
      <div className="v2-waitlist-rings" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
      </div>
      <Typography as="h2" variant="h1" id="waitlist-title" data-reveal="0">
        Seja um dos primeiros
        <br /> a usar o <span>Silent Voice.</span>
      </Typography>
      <Typography as="p" variant="body" data-reveal="1">
        Entre na lista de interesse e acompanhe
        <br className="v2-desktop-break" /> os próximos passos dessa nova forma
        de comunicar.
      </Typography>
      {status === 'success' ? (
        <div className="v2-waitlist-success" role="status">
          <span>
            <Check size={22} />
          </span>
          <div>
            <Typography as="h3" variant="h3">Você está na lista.</Typography>
            <Typography as="p" variant="body">Seu interesse foi registrado. Obrigado por fazer parte.</Typography>
          </div>
        </div>
      ) : (
        <form
          data-reveal="2"
          className="v2-waitlist-form"
          onSubmit={submit}
          noValidate
          aria-label="Lista de interesse Silent Voice"
        >
          <div className="v2-email-row">
            <svg viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path
                d="M12.75 15.375H5.25C3 15.375 1.5 14.25 1.5 11.625V6.375C1.5 3.75 3 2.625 5.25 2.625H12.75C15 2.625 16.5 3.75 16.5 6.375V11.625C16.5 14.25 15 15.375 12.75 15.375Z"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M12.75 6.75L10.4025 8.625C9.63 9.24 8.3625 9.24 7.59 8.625L5.25 6.75"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <label className="v2-sr-only" htmlFor={id}>
              Seu e-mail
            </label>
            <input
              id={id}
              type="email"
              autoComplete="email"
              inputMode="email"
              name="email"
              required
              maxLength={254}
              placeholder="Seu e-mail"
              value={email}
              readOnly={status === 'pending'}
              onChange={(e) => {
                setEmail(e.target.value)
                setInvalid(false)
                setError('')
              }}
              aria-invalid={invalid || undefined}
              aria-describedby={error ? `${id}-error` : undefined}
            />
            <button
              className="v2-button v2-button--gradient"
              disabled={status === 'pending'}
              type="submit"
            >
              {status === 'pending'
                ? 'Registrando…'
                : status === 'error'
                  ? 'Tentar novamente'
                  : 'Entrar na lista'}
            </button>
          </div>
          {error && (
            <Typography as="p" variant="caption" className="v2-form-error" id={`${id}-error`} role="alert">
              {error}
            </Typography>
          )}
          {status === 'pending' && (
            <Typography as="p" variant="caption" className="v2-form-pending" role="status">
              Confirmando seu registro. O serviço pode levar alguns instantes
              para responder.
            </Typography>
          )}
        </form>
      )}
    </section>
  )
}
