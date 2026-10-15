import { useEffect, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { leadStatuses, statusLabels } from '../../../shared/leads'
import type {
  AdminLead,
  LeadDetail,
  LeadNote,
  LeadStatus,
} from '../../../shared/leads'
import { AdminApiError, apiMessage, isAborted } from './admin-api'
import { formatAdminDate } from './admin-format'
import type { AdminRequest as Request } from './admin-api'

export type LeadDraft = { text: string; status?: LeadStatus }
const profileLabels = {
  self: 'Para mim',
  family: 'Familiar ou cuidador',
  professional: 'Profissional de saúde',
  partner: 'Parceiro ou instituição',
}
export function LeadPanel({
  id,
  request,
  draft,
  updateDraft,
  close,
  restoreFocus,
  onChange,
}: {
  id: string
  request: Request
  draft: LeadDraft
  updateDraft: (update: Partial<LeadDraft>) => void
  close: () => void
  restoreFocus: () => void
  onChange: () => void
}) {
  const [data, setData] = useState<LeadDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [revision, setRevision] = useState(0)
  const panel = useRef<HTMLElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)
  const errorRef = useRef<HTMLParagraphElement>(null)
  const mutation = useRef<AbortController | null>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeButton.current?.focus()
    return () => {
      mutation.current?.abort()
      document.body.style.overflow = previousOverflow
      if (previous?.isConnected) previous.focus()
      else restoreFocus()
    }
  }, [restoreFocus])
  useEffect(() => {
    if (error) errorRef.current?.focus()
  }, [error])
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    request<LeadDetail>(`/admin/leads/${encodeURIComponent(id)}`, {
      signal: controller.signal,
    })
      .then((value) => {
        if (!controller.signal.aborted) setData(value)
      })
      .catch((error) => {
        if (
          !isAborted(error) &&
          !(error instanceof AdminApiError && error.status === 401)
        )
          setError(
            error instanceof AdminApiError && error.status === 404
              ? 'Este contato não foi encontrado.'
              : apiMessage(error)
          )
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [id, request, revision])
  const status = draft.status ?? data?.lead.status ?? 'new'
  function keyboard(event: KeyboardEvent) {
    if (event.key === 'Escape' && !pending) {
      event.stopPropagation()
      close()
    }
    if (event.key === 'Tab') {
      const controls = panel.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]'
      )
      if (!controls?.length) return
      const first = controls[0],
        last = controls[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
  }
  async function save(kind: 'status' | 'note', event: FormEvent) {
    event.preventDefault()
    if (!data || pending) return
    setPending(true)
    setError('')
    setNotice('')
    mutation.current?.abort()
    mutation.current = new AbortController()
    const signal = mutation.current.signal
    try {
      if (kind === 'status') {
        const lead = await request<AdminLead>(
          `/admin/leads/${encodeURIComponent(id)}`,
          {
            method: 'PATCH',
            signal,
            body: JSON.stringify({ status, version: data.lead.version }),
          }
        )
        if (signal.aborted) return
        setData((previous) => (previous ? { ...previous, lead } : previous))
        updateDraft({ status: undefined })
        setNotice('Status atualizado.')
        onChange()
      } else {
        const note = await request<LeadNote>(
          `/admin/leads/${encodeURIComponent(id)}/notes`,
          {
            method: 'POST',
            signal,
            body: JSON.stringify({ text: draft.text.trim() }),
          }
        )
        if (signal.aborted) return
        setData((previous) =>
          previous
            ? { ...previous, notes: [...previous.notes, note] }
            : previous
        )
        updateDraft({ text: '' })
        setNotice('Anotação adicionada.')
      }
    } catch (error) {
      if (
        isAborted(error) ||
        (error instanceof AdminApiError && error.status === 401)
      )
        return
      if (error instanceof AdminApiError && error.status === 409) {
        setError(
          'Este contato foi atualizado por outra pessoa. Os dados foram recarregados; seu rascunho foi preservado. Confira antes de salvar novamente.'
        )
        setRevision((value) => value + 1)
      } else setError(apiMessage(error))
    } finally {
      if (!signal.aborted) setPending(false)
    }
  }
  return (
    <div
      className="admin-panel-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget && !pending) close()
      }}
    >
      <section
        className="admin-panel"
        role="dialog"
        aria-modal="true"
        aria-label={
          data ? `Contato de ${data.lead.name}` : 'Detalhes do contato'
        }
        ref={panel}
        onKeyDown={keyboard}
      >
        <header className="admin-panel-top">
          <span className="admin-eyebrow">DETALHES DO CONTATO</span>
          <button
            ref={closeButton}
            type="button"
            className="admin-close"
            aria-label="Fechar detalhes"
            onClick={close}
            disabled={pending}
          >
            ×
          </button>
        </header>
        {error && (
          <p
            className="admin-error admin-panel-message"
            role="alert"
            ref={errorRef}
            tabIndex={-1}
          >
            {error}
          </p>
        )}
        {notice && (
          <p className="admin-notice admin-panel-message" role="status">
            {notice}
          </p>
        )}
        {loading && (
          <div className="admin-panel-message" role="status">
            Atualizando contato…
          </div>
        )}
        {!data && !loading && (
          <div className="admin-panel-message">
            <button
              className="admin-button"
              onClick={() => {
                setError('')
                setRevision((value) => value + 1)
              }}
            >
              Tentar novamente
            </button>
          </div>
        )}
        {data && (
          <div className="admin-panel-body">
            <div className="admin-person">
              <span
                className="admin-avatar admin-avatar-large"
                aria-hidden="true"
              >
                {data.lead.name.trim().slice(0, 1).toLocaleUpperCase('pt-BR')}
              </span>
              <h2>{data.lead.name}</h2>
              <a href={`mailto:${data.lead.email}`}>{data.lead.email}</a>
              {data.lead.duplicateEmail && (
                <span className="admin-duplicate">E-mail repetido</span>
              )}
            </div>
            <dl className="admin-details">
              <div>
                <dt>Recebido em</dt>
                <dd>{formatAdminDate(data.lead.createdAt)}</dd>
              </div>
              {data.lead.profile && (
                <div>
                  <dt>Perfil</dt>
                  <dd>{profileLabels[data.lead.profile]}</dd>
                </div>
              )}
              {data.lead.organization && (
                <div>
                  <dt>Organização</dt>
                  <dd>{data.lead.organization}</dd>
                </div>
              )}
              <div className="admin-details-wide">
                <dt>Objetivo</dt>
                <dd>{data.lead.objective}</dd>
              </div>
            </dl>
            <form
              className="admin-status-form"
              onSubmit={(event) => void save('status', event)}
            >
              <h3>Acompanhamento</h3>
              <label className="admin-field">
                Status do contato
                <select
                  value={status}
                  disabled={pending || loading}
                  onChange={(event) =>
                    updateDraft({ status: event.target.value as LeadStatus })
                  }
                >
                  {leadStatuses.map((item) => (
                    <option value={item} key={item}>
                      {statusLabels[item]}
                    </option>
                  ))}
                </select>
              </label>
              <p className="admin-help">
                “Demonstração combinada” é um registro manual. Não agenda um
                evento no calendário.
              </p>
              <button
                className="admin-button"
                type="submit"
                disabled={pending || loading || status === data.lead.status}
              >
                {pending ? 'Salvando…' : 'Salvar status'}
              </button>
            </form>
            <section
              className="admin-notes"
              aria-labelledby="admin-notes-title"
            >
              <h3 id="admin-notes-title">
                Anotações <span>{data.notes.length}</span>
              </h3>
              <form onSubmit={(event) => void save('note', event)}>
                <label className="admin-field">
                  Nova anotação
                  <textarea
                    placeholder="Registre um próximo passo ou contexto…"
                    value={draft.text}
                    disabled={pending}
                    onChange={(event) =>
                      updateDraft({ text: event.target.value })
                    }
                    maxLength={2000}
                    rows={4}
                  />
                </label>
                <div className="admin-note-submit">
                  <span>{draft.text.length}/2000</span>
                  <button
                    type="submit"
                    className="admin-button admin-button-primary"
                    disabled={pending || loading || !draft.text.trim()}
                  >
                    Adicionar anotação
                  </button>
                </div>
              </form>
              {data.notes.length ? (
                <ol className="admin-note-list">
                  {[...data.notes].reverse().map((note) => (
                    <li key={note.id}>
                      <p>{note.text}</p>
                      <div>
                        <span>{note.author}</span>
                        <time dateTime={note.createdAt}>
                          {formatAdminDate(note.createdAt)}
                        </time>
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="admin-help admin-no-notes">
                  Nenhuma anotação ainda. Registre o primeiro próximo passo.
                </p>
              )}
            </section>
          </div>
        )}
      </section>
    </div>
  )
}
