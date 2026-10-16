import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { leadStatuses, statusLabels } from '../../../shared/leads'
import type { LeadList, LeadStatus } from '../../../shared/leads'
import { AdminApiError, apiMessage, isAborted } from './admin-api'
import type { AdminRequest } from './admin-api'
import { formatAdminDate } from './admin-format'
import { AdminIcon } from './AdminIcon'
import { AdminButton } from './AdminButton'
import { LeadPanel } from './LeadPanel'
import type { LeadDraft } from './LeadPanel'
import { exportLeadPage } from './lead-export'
import './contacts.css'

type Filters = { q: string; status: string; from: string; to: string }

function validStatus(value: string | null) {
  return leadStatuses.includes(value as LeadStatus) ? value! : ''
}

export function ContactsPage({
  request,
  drafts,
  updateDraft,
  view = 'register',
}: {
  request: AdminRequest
  drafts: Record<string, LeadDraft>
  updateDraft: (id: string, update: Partial<LeadDraft>) => void
  view?: 'register' | 'tracking'
}) {
  const [searchParams, setSearchParams] = useSearchParams()
  const tracking = view === 'tracking'
  const sidebarStatus = validStatus(searchParams.get('status')) || (tracking ? 'new' : '')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState(sidebarStatus)
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [filters, setFilters] = useState<Filters>({
    q: '',
    status: sidebarStatus,
    from: '',
    to: '',
  })
  const [showFilters, setShowFilters] = useState(false)
  const [page, setPage] = useState(1)
  const [data, setData] = useState<LeadList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const listHeading = useRef<HTMLHeadingElement>(null)
  const searchInput = useRef<HTMLInputElement>(null)
  const filterToggle = useRef<HTMLButtonElement>(null)
  const filterPopover = useRef<HTMLDivElement>(null)
  const leadActions = useRef(new Map<string, HTMLButtonElement>())
  const restoreFocus = useCallback(() => {
    const action = selected ? leadActions.current.get(selected) : undefined
    ;(action?.isConnected ? action : listHeading.current)?.focus()
  }, [selected])
  const filterError =
    from && to && from > to
      ? 'A data inicial deve ser anterior ou igual à data final.'
      : ''
  const hasFilters = Boolean(
    filters.q || (!tracking && filters.status) || filters.from || filters.to
  )

  useEffect(() => {
    setStatus(sidebarStatus)
    setPage(1)
    setFilters((previous) =>
      previous.status === sidebarStatus
        ? previous
        : { ...previous, status: sidebarStatus }
    )
  }, [sidebarStatus])

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams({ page: String(page) })
    for (const [key, value] of Object.entries(filters))
      if (value) params.set(key, value)
    setLoading(true)
    setError('')
    setData(null)
    request<LeadList>(`/admin/leads?${params}`, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setData(result)
      })
      .catch((reason) => {
        if (
          !controller.signal.aborted &&
          !isAborted(reason) &&
          !(reason instanceof AdminApiError && reason.status === 401)
        )
          setError(apiMessage(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [request, filters, page, refresh])

  function syncStatus(value: string) {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous)
      if (value) next.set('status', value)
      else next.delete('status')
      return next
    })
  }

  function applyFilters(event: FormEvent) {
    event.preventDefault()
    if (filterError) {
      setShowFilters(true)
      return
    }
    setPage(1)
    setFilters({ q: query.trim(), status, from, to })
    if (status !== sidebarStatus) syncStatus(status)
    if (filterPopover.current?.contains(document.activeElement))
      filterToggle.current?.focus()
    setShowFilters(false)
  }

  function clearFilters(restoreSearch = false) {
    setQuery('')
    const nextStatus = tracking ? sidebarStatus : ''
    setStatus(nextStatus)
    setFrom('')
    setTo('')
    setPage(1)
    setFilters({ q: '', status: nextStatus, from: '', to: '' })
    syncStatus(nextStatus)
    if (restoreSearch) searchInput.current?.focus()
  }

  return (
    <section className="admin-contacts-page" aria-labelledby="admin-list-title">
      <h1
        id="admin-list-title"
        className="admin-visually-hidden"
        ref={listHeading}
        tabIndex={-1}
      >
        {tracking ? 'Acompanhamento de contatos' : 'Todos os contatos'} <span>{data ? data.total : '—'}</span>
      </h1>
      <form
        className="admin-contacts-toolbar"
        aria-label="Filtrar contatos"
        onSubmit={applyFilters}
      >
        <label className="admin-contacts-search">
          <span className="admin-visually-hidden">Buscar</span>
          <AdminIcon name="search" />
          <input
            ref={searchInput}
            type="search"
            placeholder="Buscar contatos…"
            maxLength={200}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <div className="admin-contacts-toolbar-actions">
          {!tracking && (
            <>
              <label className="admin-contacts-status-filter">
                <span className="admin-visually-hidden">Status</span>
                <AdminIcon name="file" />
                <select
                  value={status}
                  onChange={(event) => {
                    const value = event.target.value
                    setStatus(value)
                    setPage(1)
                    setFilters((previous) => ({ ...previous, status: value }))
                    syncStatus(value)
                  }}
                >
                  <option value="">Todos os status</option>
                  {leadStatuses.map((item) => (
                    <option key={item} value={item}>
                      {statusLabels[item]}
                    </option>
                  ))}
                </select>
                <AdminIcon name="chevron-down" />
              </label>
              <span className="admin-contacts-toolbar-divider" aria-hidden="true" />
            </>
          )}
          <div
            className="admin-contacts-filter-anchor"
            onKeyDown={(event) => {
              if (event.key === 'Escape' && showFilters) {
                event.preventDefault()
                event.stopPropagation()
                setShowFilters(false)
                filterToggle.current?.focus()
              }
            }}
          >
            <AdminButton
              type="button"
              ref={filterToggle}
              aria-label="Filtros"
              aria-expanded={showFilters}
              aria-controls="admin-contact-filters"
              onClick={() => setShowFilters((value) => !value)}
            >
              <AdminIcon name="filter" />
              Filtros
              {(filters.from || filters.to) && (
                <span className="admin-contacts-filter-dot" aria-label="Datas aplicadas" />
              )}
              <AdminIcon name="chevron-down" />
            </AdminButton>
            {showFilters && (
              <div
                ref={filterPopover}
                className="admin-contacts-filter-popover"
                id="admin-contact-filters"
              >
                <p>Data de recebimento</p>
                <div className="admin-contacts-date-fields">
                  <label className="admin-field">
                    De
                    <input
                      type="date"
                      value={from}
                      onChange={(event) => setFrom(event.target.value)}
                    />
                  </label>
                  <label className="admin-field">
                    Até
                    <input
                      type="date"
                      value={to}
                      min={from || undefined}
                      onChange={(event) => setTo(event.target.value)}
                    />
                  </label>
                </div>
                {filterError && <p className="admin-contacts-filter-error" role="alert">{filterError}</p>}
                <div className="admin-contacts-filter-footer">
                  <AdminButton type="button" onClick={() => clearFilters()}>
                    Limpar
                  </AdminButton>
                  <AdminButton type="submit" variant="primary" disabled={Boolean(filterError)}>
                    Filtrar
                  </AdminButton>
                </div>
              </div>
            )}
          </div>
          <AdminButton
            type="button"
            className="admin-contacts-refresh"
            aria-label="Atualizar contatos"
            disabled={loading}
            onClick={() => setRefresh((value) => value + 1)}
          >
            <AdminIcon name="refresh" />
            Atualizar
          </AdminButton>
          <span className="admin-contacts-toolbar-divider" aria-hidden="true" />
          <AdminButton
            type="button"
            variant="primary"
            disabled={loading || !data?.items.length}
            onClick={() => data && exportLeadPage(data.items)}
          >
            <AdminIcon name="export" />
            Exportar página
          </AdminButton>
        </div>
      </form>
      {tracking && (
        <nav className="admin-tracking-statuses" aria-label="Status do acompanhamento" aria-busy={loading}>
          {leadStatuses.map((item) => (
            <Link
              key={item}
              className="admin-tracking-status"
              to={`/admin/acompanhamento?status=${item}`}
              aria-current={sidebarStatus === item ? 'page' : undefined}
              aria-label={`${statusLabels[item]}: ${data ? data.counts[item] : 'carregando'} contatos`}
            >
              <span>{statusLabels[item]}</span>
              <span className="admin-tracking-count" aria-hidden="true">{data ? data.counts[item] : '—'}</span>
            </Link>
          ))}
        </nav>
      )}
      {hasFilters && (
        <div className="admin-contacts-active-filters">
          <span>
            {[
              filters.q && `Busca: ${filters.q}`,
              !tracking && filters.status && statusLabels[filters.status as LeadStatus],
              filters.from && `De ${filters.from.split('-').reverse().join('/')}`,
              filters.to && `Até ${filters.to.split('-').reverse().join('/')}`,
            ].filter(Boolean).join(' · ')}
          </span>
          <AdminButton type="button" onClick={() => clearFilters(true)}>
            Limpar filtros
          </AdminButton>
        </div>
      )}
      <div className={`admin-contacts-content${selected ? ' admin-contacts-content-inspecting' : ''}`}>
        <div className="admin-contacts-list">
          {error && (
            <div className="admin-contacts-state">
              <p role="alert" className="admin-error">{error}</p>
              <AdminButton onClick={() => setRefresh((value) => value + 1)}>
                Tentar novamente
              </AdminButton>
            </div>
          )}
          {loading ? (
            <div className="admin-contacts-state" role="status">
              <div className="admin-loader" />
              Carregando contatos…
            </div>
          ) : data?.items.length ? (
            <div className="admin-contacts-table-wrap">
              <table className="admin-contacts-table">
                <colgroup>
                  <col className="admin-contacts-col-open" />
                  <col className="admin-contacts-col-name" />
                  <col className="admin-contacts-col-email" />
                  <col className="admin-contacts-col-objective" />
                  <col className="admin-contacts-col-status" />
                  <col className="admin-contacts-col-date" />
                </colgroup>
                <thead>
                  <tr>
                    <th scope="col"><span className="admin-visually-hidden">Detalhes</span></th>
                    <th scope="col"><span className="admin-contacts-column-title"><AdminIcon name="contacts" /> Nome</span></th>
                    <th scope="col"><span className="admin-contacts-column-title"><AdminIcon name="mail" /> E-mail</span></th>
                    <th scope="col"><span className="admin-contacts-column-title"><AdminIcon name="file" /> Objetivo</span></th>
                    <th scope="col">Status</th>
                    <th scope="col">Recebido em</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((lead) => (
                    <tr key={lead.id} className={selected === lead.id ? 'admin-contacts-row-selected' : undefined}>
                      <td>
                        <button
                          className="admin-contacts-row-open"
                          type="button"
                          aria-label={`Abrir detalhes de ${lead.name}`}
                          aria-pressed={selected === lead.id}
                          onClick={() => setSelected(lead.id)}
                        >
                          <AdminIcon name="chevron-right" />
                        </button>
                      </td>
                      <td>
                        <button
                          className="admin-contacts-name"
                          type="button"
                          ref={(element) => {
                            if (element) leadActions.current.set(lead.id, element)
                            else leadActions.current.delete(lead.id)
                          }}
                          onClick={() => setSelected(lead.id)}
                          aria-label={`Ver contato de ${lead.name}`}
                          title={lead.name}
                        >
                          <span className="admin-contacts-initial" aria-hidden="true">{lead.name.trim().slice(0, 1).toLocaleUpperCase('pt-BR')}</span>
                          <span>{lead.name}</span>
                        </button>
                      </td>
                      <td>
                        <a className="admin-contacts-email" href={`mailto:${lead.email}`} title={lead.email}>{lead.email}</a>
                      </td>
                      <td><span className="admin-contacts-cell-text" title={lead.objective}>{lead.objective}</span></td>
                      <td>
                        <span className={`admin-contacts-status admin-contacts-status-${lead.status}`} title={statusLabels[lead.status]}>
                          <span className="admin-contacts-status-dot" aria-hidden="true" />
                          <span className="admin-contacts-status-label">{statusLabels[lead.status]}</span>
                        </span>
                      </td>
                      <td><time dateTime={lead.createdAt}>{formatAdminDate(lead.createdAt)}</time></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : data && (
            <div className="admin-contacts-state">
              <AdminIcon name="contacts" />
              <h3>Nenhum contato encontrado</h3>
              <p>{hasFilters ? 'Experimente ajustar os filtros da busca.' : 'Os contatos recebidos pelo site aparecerão aqui.'}</p>
            </div>
          )}
          <div className="admin-contacts-pagination">
            <span>
              {data?.total
                ? `${(page - 1) * 25 + 1}–${Math.min(page * 25, data.total)} de ${data.total} contatos`
                : loading ? 'Carregando…' : '0 contatos'}
            </span>
            <nav aria-label="Paginação dos contatos">
              <AdminButton
                disabled={loading || page <= 1}
                onClick={() => setPage((value) => value - 1)}
              >← Anterior</AdminButton>
              <span>Página {page}</span>
              <AdminButton
                disabled={loading || !data || page * 25 >= data.total}
                onClick={() => setPage((value) => value + 1)}
              >Próxima →</AdminButton>
            </nav>
          </div>
        </div>
        {selected && (
          <LeadPanel
            key={selected}
            mode="inline"
            id={selected}
            request={request}
            draft={drafts[selected] ?? { text: '' }}
            updateDraft={(update) => updateDraft(selected, update)}
            close={() => setSelected(null)}
            restoreFocus={restoreFocus}
            onChange={() => {
              setPage(1)
              setRefresh((value) => value + 1)
            }}
          />
        )}
      </div>
    </section>
  )
}
