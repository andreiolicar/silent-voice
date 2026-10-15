import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import type { LeadInput, LeadProfile, LeadReceipt } from '../../../shared/leads'

type Fields = {
  name: string
  email: string
  objective: string
  profile: '' | LeadProfile
  organization: string
}
type Submission = { payload: Readonly<LeadInput>; body: string; key: string }
type Status = 'editing' | 'pending' | 'unknown' | 'confirmed'
const labels = {
  name: 'Nome',
  email: 'E-mail',
  objective: 'Objetivo do contato',
  profile: 'Perfil (opcional)',
  organization: 'Organização (opcional)',
}
const empty: Fields = {
  name: '',
  email: '',
  objective: '',
  profile: '',
  organization: '',
}
function validate(fields: Fields) {
  const errors: Partial<Record<keyof Fields, string>> = {}
  if (fields.name.trim().length < 2 || fields.name.trim().length > 100)
    errors.name = 'Informe seu nome, entre 2 e 100 caracteres.'
  if (
    fields.email.length > 254 ||
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email.trim())
  )
    errors.email = 'Informe um e-mail válido.'
  if (
    fields.objective.trim().length < 10 ||
    fields.objective.trim().length > 1000
  )
    errors.objective = 'Conte seu objetivo, entre 10 e 1000 caracteres.'
  if (fields.organization.trim().length > 150)
    errors.organization = 'Use até 150 caracteres.'
  return errors
}
function isReceipt(value: unknown): value is LeadReceipt {
  return (
    !!value &&
    typeof value === 'object' &&
    'id' in value &&
    typeof value.id === 'string' &&
    value.id.trim().length > 0 &&
    value.id.length <= 100 &&
    'createdAt' in value &&
    typeof value.createdAt === 'string' &&
    Number.isFinite(Date.parse(value.createdAt))
  )
}
export function ChatLeadForm() {
  const id = useId()
  const [fields, setFields] = useState<Fields>(empty)
  const [errors, setErrors] = useState<Partial<Record<keyof Fields, string>>>(
    {}
  )
  const [status, setStatus] = useState<Status>('editing')
  const [notice, setNotice] = useState('')
  const snapshot = useRef<Submission | null>(null)
  const controller = useRef<AbortController | null>(null)
  const revision = useRef(0)
  const pending = useRef(false)
  const uncertain = useRef(false)
  useEffect(
    () => () => {
      revision.current++
      controller.current?.abort()
    },
    []
  )
  const locked = status === 'pending' || status === 'unknown'
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (pending.current) return
    if (!snapshot.current) {
      const nextErrors = validate(fields)
      setErrors(nextErrors)
      if (Object.keys(nextErrors).length) return
      const payload = Object.freeze({
        name: fields.name.trim(),
        email: fields.email.trim(),
        objective: fields.objective.trim(),
        ...(fields.profile ? { profile: fields.profile } : {}),
        ...(fields.organization.trim()
          ? { organization: fields.organization.trim() }
          : {}),
      })
      snapshot.current = {
        payload,
        body: JSON.stringify(payload),
        key: crypto.randomUUID(),
      }
    }
    const submission = snapshot.current
    const requestRevision = ++revision.current
    const aborter = new AbortController()
    controller.current = aborter
    pending.current = true
    setStatus('pending')
    setNotice('')
    let timer: ReturnType<typeof setTimeout> | undefined
    try {
      const timeout = new Promise<never>((_, reject) => {
        timer = setTimeout(() => {
          aborter.abort()
          reject(new Error('confirmation-timeout'))
        }, 15000)
      })
      // Race the whole receipt operation: a response whose body stalls is also unknown.
      const result = await Promise.race([
        timeout,
        (async () => {
          const response = await fetch('/api/leads', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Idempotency-Key': submission.key,
            },
            body: submission.body,
            signal: aborter.signal,
          })
          // A later rejection cannot resolve an earlier possible commit.
          if (response.status === 400 && !uncertain.current)
            return { kind: 'invalid' as const }
          if (response.status !== 200 && response.status !== 201)
            throw new Error('unconfirmed-status')
          const value: unknown = await response.json()
          if (!isReceipt(value)) throw new Error('invalid-receipt')
          return { kind: 'confirmed' as const }
        })(),
      ])
      if (revision.current !== requestRevision) return
      if (result.kind === 'invalid') {
        snapshot.current = null
        setStatus('editing')
        setNotice(
          'Revise as informações e tente novamente. O registro não foi confirmado.'
        )
      } else {
        setStatus('confirmed')
      }
    } catch {
      if (revision.current !== requestRevision) return
      uncertain.current = true
      setStatus('unknown')
      setNotice(
        'Não foi possível confirmar o registro. Você pode tentar novamente com as mesmas informações.'
      )
    } finally {
      clearTimeout(timer)
      if (revision.current === requestRevision) {
        pending.current = false
        controller.current = null
      }
    }
  }
  const fieldProps = (name: keyof Fields) => ({
    id: `${id}-${name}`,
    name,
    value: fields[name],
    readOnly: locked,
    'aria-invalid': errors[name] ? true : undefined,
    'aria-describedby': errors[name] ? `${id}-${name}-error` : undefined,
    onChange: (
      event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
    ) => setFields((current) => ({ ...current, [name]: event.target.value })),
  })
  return (
    <div className="sv-lead">
      {status === 'confirmed' ? (
        <div className="sv-lead-success" role="status">
          <span aria-hidden="true" className="sv-lead-success-icon">
            ✓
          </span>
          <h3 tabIndex={-1} data-contact-receipt>Seu interesse foi registrado.</h3>
          <p>Nossa equipe poderá entrar em contato pelo e-mail informado.</p>
        </div>
      ) : (
        <>
          <h3>Vamos conversar?</h3>
          <p>
            Usaremos estas informações para conversar com você sobre seu
            interesse no Silent Voice.
          </p>
          <form
            onSubmit={submit}
            noValidate
            aria-label="Registrar interesse no Silent Voice"
          >
            <div className="sv-field">
              <label htmlFor={`${id}-name`}>{labels.name}</label>
              <input
                {...fieldProps('name')}
                autoComplete="name"
                maxLength={100}
                required
              />
              {errors.name && (
                <span id={`${id}-name-error`} className="sv-field-error">
                  {errors.name}
                </span>
              )}
            </div>
            <div className="sv-field">
              <label htmlFor={`${id}-email`}>{labels.email}</label>
              <input
                {...fieldProps('email')}
                type="email"
                autoComplete="email"
                maxLength={254}
                required
              />
              {errors.email && (
                <span id={`${id}-email-error`} className="sv-field-error">
                  {errors.email}
                </span>
              )}
            </div>
            <div className="sv-field">
              <label htmlFor={`${id}-objective`}>{labels.objective}</label>
              <textarea
                {...fieldProps('objective')}
                rows={3}
                maxLength={1000}
                required
              />
              {errors.objective && (
                <span id={`${id}-objective-error`} className="sv-field-error">
                  {errors.objective}
                </span>
              )}
            </div>
            <div className="sv-field">
              <label htmlFor={`${id}-profile`}>{labels.profile}</label>
              <select
                id={`${id}-profile`}
                name="profile"
                disabled={locked}
                value={fields.profile}
                onChange={(event) =>
                  setFields((current) => ({
                    ...current,
                    profile: event.target.value as Fields['profile'],
                  }))
                }
              >
                <option value="">Selecione, se desejar</option>
                <option value="self">Pessoa interessada</option>
                <option value="family">Familiar ou cuidador</option>
                <option value="professional">
                  Profissional ou instituição
                </option>
                <option value="partner">Parceiro</option>
              </select>
            </div>
            <div className="sv-field">
              <label htmlFor={`${id}-organization`}>
                {labels.organization}
              </label>
              <input
                {...fieldProps('organization')}
                autoComplete="organization"
                maxLength={150}
              />
              {errors.organization && (
                <span
                  id={`${id}-organization-error`}
                  className="sv-field-error"
                >
                  {errors.organization}
                </span>
              )}
            </div>
            {notice && (
              <p className="sv-chat-notice" role="alert">
                {notice}
              </p>
            )}
            <button
              className="sv-primary-button"
              type="submit"
              disabled={status === 'pending'}
            >
              {status === 'pending'
                ? 'Confirmando registro…'
                : status === 'unknown'
                  ? 'Tentar confirmar novamente'
                  : 'Registrar interesse'}
            </button>
          </form>
          <p className="sv-lead-privacy">
            Esses campos não são enviados automaticamente à IA. Não inclua
            diagnósticos ou dados clínicos.
          </p>
        </>
      )}
      <p className="sv-contact-email">
        Você também pode escrever para{' '}
        <a href="mailto:contato@silentvoice.com.br">
          contato@silentvoice.com.br
        </a>
        .
      </p>
    </div>
  )
}
