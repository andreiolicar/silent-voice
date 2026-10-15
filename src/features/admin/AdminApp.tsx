import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom'
import { leadStatuses, statusLabels } from '../../../shared/leads'
import type { LeadList } from '../../../shared/leads'
import { AdminApiError, adminFetch, apiMessage, isAborted } from './admin-api'
import type { Session, AdminRequest as Request } from './admin-api'
import { formatAdminDate } from './admin-format'
import { LeadPanel } from './LeadPanel'
import type { LeadDraft } from './LeadPanel'
import { Brand } from '../../components/Brand'
import { Login } from './Login'
import './admin.css'

export function AdminApp() {
  const navigate = useNavigate()
  const location = useLocation()
  const [session, setSession] = useState<Session | null>(null)
  const [checking, setChecking] = useState(true)
  const [sessionError, setSessionError] = useState('')
  const [sessionRetry, setSessionRetry] = useState(0)
  const [expired, setExpired] = useState(false)
  const [drafts, setDrafts] = useState<Record<string, LeadDraft>>({})
  const login = location.pathname === '/admin/login'
  const expire = useCallback(() => {
    setSession(null)
    setExpired(true)
    navigate('/admin/login', { replace: true })
  }, [navigate])
  useEffect(() => {
    if (login || session) {
      setChecking(false)
      return
    }
    const controller = new AbortController()
    setChecking(true)
    setSessionError('')
    adminFetch<Session>('/auth/session', { signal: controller.signal })
      .then(setSession)
      .catch((error) => {
        if (isAborted(error)) return
        if (error instanceof AdminApiError && error.status === 401) expire()
        else setSessionError(apiMessage(error))
      })
      .finally(() => {
        if (!controller.signal.aborted) setChecking(false)
      })
    return () => controller.abort()
  }, [login, session, sessionRetry, expire])
  const request: Request = useCallback(
    async <T,>(path: string, options?: RequestInit) => {
      try {
        return await adminFetch<T>(path, options, session?.csrfToken)
      } catch (error) {
        if (error instanceof AdminApiError && error.status === 401) expire()
        throw error
      }
    },
    [session?.csrfToken, expire]
  )
  const updateDraft = useCallback((id: string, update: Partial<LeadDraft>) => {
    setDrafts((previous) => ({
      ...previous,
      [id]: { ...(previous[id] ?? { text: '' }), ...update },
    }))
  }, [])
  return (
    <div className="admin-shell">
      <Routes>
        <Route
          path="/admin/login"
          element={
            <Login
              expired={expired}
              onLogin={(value) => {
                setSession(value)
                setExpired(false)
                navigate('/admin', { replace: true })
              }}
            />
          }
        />
        <Route
          path="/admin"
          element={
            checking ? (
              <div className="admin-boot" role="status">
                Carregando área de gestão…
              </div>
            ) : sessionError ? (
              <div className="admin-boot">
                <p role="alert">{sessionError}</p>
                <button
                  className="admin-button"
                  onClick={() => setSessionRetry((value) => value + 1)}
                >
                  Tentar novamente
                </button>
              </div>
            ) : session ? (
              <Dashboard
                email={session.user.email}
                request={request}
                drafts={drafts}
                updateDraft={updateDraft}
                onLogout={() => {
                  setSession(null)
                  setDrafts({})
                  setExpired(false)
                  navigate('/admin/login', { replace: true })
                }}
              />
            ) : (
              <Navigate to="/admin/login" replace />
            )
          }
        />
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    </div>
  )
}

function Dashboard({
  email,
  request,
  onLogout,
  drafts,
  updateDraft,
}: {
  email: string
  request: Request
  onLogout: () => void
  drafts: Record<string, LeadDraft>
  updateDraft: (id: string, update: Partial<LeadDraft>) => void
}) {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [filters, setFilters] = useState({
    q: '',
    status: '',
    from: '',
    to: '',
  })
  const [page, setPage] = useState(1)
  const [data, setData] = useState<LeadList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [loggingOut, setLoggingOut] = useState(false)
  const logoutController = useRef<AbortController | null>(null)
  const listHeading = useRef<HTMLHeadingElement>(null)
  const leadActions = useRef(new Map<string, HTMLButtonElement>())
  const restoreFocus = useCallback(() => {
    const action = selected ? leadActions.current.get(selected) : undefined
    ;(action?.isConnected ? action : listHeading.current)?.focus()
  }, [selected])
  const filterError =
    from && to && from > to
      ? 'A data inicial deve ser anterior ou igual à data final.'
      : ''
  useEffect(() => () => logoutController.current?.abort(), [])
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
      .catch((error) => {
        if (
          !isAborted(error) &&
          !(error instanceof AdminApiError && error.status === 401)
        )
          setError(apiMessage(error))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [request, filters, page, refresh])
  async function logout() {
    setLoggingOut(true)
    setError('')
    logoutController.current = new AbortController()
    try {
      await request('/auth/logout', {
        method: 'POST',
        signal: logoutController.current.signal,
      })
      onLogout()
    } catch (error) {
      if (!isAborted(error)) setError(apiMessage(error))
    } finally {
      if (!logoutController.current.signal.aborted) setLoggingOut(false)
    }
  }
  function applyFilters(event: FormEvent) {
    event.preventDefault()
    if (!filterError) {
      setPage(1)
      setFilters({ q: query.trim(), status, from, to })
    }
  }
  return (
    <>
      <header className="admin-header">
        <Brand href="/" size="small" />
        <div className="admin-header-account">
          <span>{email}</span>
          <button
            className="admin-button admin-button-quiet"
            onClick={logout}
            disabled={loggingOut}
          >
            {loggingOut ? 'Saindo…' : 'Sair'}
          </button>
        </div>
      </header>
      <main className="admin-main" id="admin-content">
        <div className="admin-page-heading">
          <div>
            <div className="admin-eyebrow">RELACIONAMENTOS</div>
            <h1>Contatos</h1>
            <p>Boas conversas começam com atenção.</p>
          </div>
          <span className="admin-live-label">
            <span /> Gestão de contatos
          </span>
        </div>
        <section className="admin-metrics" aria-label="Resumo dos contatos">
          {leadStatuses.map((item) => (
            <button
              key={item}
              type="button"
              className={`admin-metric ${filters.status === item ? 'admin-metric-active' : ''}`}
              onClick={() => {
                setStatus(item)
                setPage(1)
                setFilters((previous) => ({ ...previous, status: item }))
              }}
              aria-label={`${statusLabels[item]}: ${data ? data.counts[item] : 'carregando'} contatos`}
              aria-pressed={filters.status === item}
            >
              <span className={`admin-status-dot admin-status-dot-${item}`} />
              <span>{statusLabels[item]}</span>
              <strong>{data ? data.counts[item] : '—'}</strong>
            </button>
          ))}
        </section>
        <section className="admin-list-card" aria-labelledby="admin-list-title">
          <div className="admin-list-heading">
            <h2 id="admin-list-title" ref={listHeading} tabIndex={-1}>
              Todos os contatos <span>{data ? data.total : '—'}</span>
            </h2>
            <span>25 por página</span>
          </div>
          <form className="admin-filters" onSubmit={applyFilters}>
            <label className="admin-field admin-search">
              Buscar
              <input
                type="search"
                maxLength={200}
                placeholder="Nome, e-mail ou objetivo"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
            <label className="admin-field">
              Status
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="">Todos os status</option>
                {leadStatuses.map((item) => (
                  <option key={item} value={item}>
                    {statusLabels[item]}
                  </option>
                ))}
              </select>
            </label>
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
            <button
              className="admin-button admin-button-filter"
              disabled={!!filterError}
            >
              Filtrar
            </button>
            {(filters.q || filters.status || filters.from || filters.to) && (
              <button
                type="button"
                className="admin-button admin-button-quiet"
                onClick={() => {
                  setQuery('')
                  setStatus('')
                  setFrom('')
                  setTo('')
                  setPage(1)
                  setFilters({ q: '', status: '', from: '', to: '' })
                }}
              >
                Limpar
              </button>
            )}
          </form>
          {filterError && (
            <p className="admin-error admin-inline-message" role="alert">
              {filterError}
            </p>
          )}
          {error && (
            <div className="admin-inline-message">
              <p role="alert" className="admin-error">
                {error}
              </p>
              <button
                className="admin-button"
                onClick={() => setRefresh((value) => value + 1)}
              >
                Tentar novamente
              </button>
            </div>
          )}
          {loading ? (
            <div className="admin-list-state" role="status">
              <div className="admin-loader" />
              Carregando contatos…
            </div>
          ) : data?.items.length ? (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th scope="col">Contato</th>
                    <th scope="col">Objetivo</th>
                    <th scope="col">Status</th>
                    <th scope="col">Recebido em</th>
                    <th scope="col">
                      <span className="admin-visually-hidden">Detalhes</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((lead) => (
                    <tr key={lead.id}>
                      <td>
                        <button
                          className="admin-contact"
                          ref={(element) => {
                            if (element)
                              leadActions.current.set(lead.id, element)
                            else leadActions.current.delete(lead.id)
                          }}
                          onClick={() => setSelected(lead.id)}
                          aria-label={`Ver contato de ${lead.name}`}
                        >
                          <span className="admin-avatar" aria-hidden="true">
                            {lead.name
                              .trim()
                              .slice(0, 1)
                              .toLocaleUpperCase('pt-BR')}
                          </span>
                          <span>
                            <strong>{lead.name}</strong>
                            <span>
                              {lead.email}
                              {lead.duplicateEmail && (
                                <span
                                  className="admin-duplicate"
                                  title="Há outros contatos com este e-mail"
                                >
                                  E-mail repetido
                                </span>
                              )}
                            </span>
                          </span>
                        </button>
                      </td>
                      <td className="admin-objective">
                        <span>{lead.objective}</span>
                      </td>
                      <td>
                        <span
                          className={`admin-badge admin-badge-${lead.status}`}
                        >
                          {statusLabels[lead.status]}
                        </span>
                      </td>
                      <td className="admin-date">
                        {formatAdminDate(lead.createdAt)}
                      </td>
                      <td>
                        <button
                          className="admin-row-open"
                          aria-label={`Abrir detalhes de ${lead.name}`}
                          onClick={() => setSelected(lead.id)}
                        >
                          ↗
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            data && (
              <div className="admin-list-state">
                <span className="admin-empty-icon" aria-hidden="true">
                  ⌑
                </span>
                <h3>Nenhum contato encontrado</h3>
                <p>
                  {filters.q || filters.status || filters.from || filters.to
                    ? 'Experimente ajustar os filtros da busca.'
                    : 'Os contatos recebidos pelo site aparecerão aqui.'}
                </p>
              </div>
            )
          )}
          <div className="admin-pagination">
            <span>
              {data?.total
                ? `${(page - 1) * 25 + 1}–${Math.min(page * 25, data.total)} de ${data.total} contatos`
                : '0 contatos'}{' '}
            </span>
            <nav aria-label="Paginação dos contatos">
              <button
                className="admin-button admin-button-quiet"
                disabled={loading || page <= 1}
                onClick={() => setPage((value) => value - 1)}
              >
                ← Anterior
              </button>
              <span>Página {page}</span>
              <button
                className="admin-button admin-button-quiet"
                disabled={loading || !data || page * 25 >= data.total}
                onClick={() => setPage((value) => value + 1)}
              >
                Próxima →
              </button>
            </nav>
          </div>
        </section>
        <footer className="admin-footer">
          Silent Voice <span>Pequenos passos. Novas possibilidades.</span>
        </footer>
      </main>
      {selected && (
        <LeadPanel
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
    </>
  )
}
