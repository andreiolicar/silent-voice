import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { leadStatuses, statusLabels } from '../../../shared/leads'
import type { LeadList } from '../../../shared/leads'
import { AdminApiError, apiMessage, isAborted } from './admin-api'
import type { AdminRequest } from './admin-api'
import { formatAdminDate } from './admin-format'
import { AdminIcon } from './AdminIcon'
import './overview.css'

export function Overview({ request }: { request: AdminRequest }) {
  const [data, setData] = useState<LeadList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    setData(null)
    request<LeadList>('/admin/leads?page=1', { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setData(result)
      })
      .catch((reason: unknown) => {
        if (
          !controller.signal.aborted &&
          !isAborted(reason) &&
          !(reason instanceof AdminApiError && reason.status === 401)
        ) setError(apiMessage(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [request, retry])

  const total = data
    ? leadStatuses.reduce((sum, status) => sum + data.counts[status], 0)
    : null

  return (
    <div className="crm-overview">
      <div className="crm-overview-heading">
        <div>
          <h1>Visão geral</h1>
          <p>Acompanhe os cadastros recebidos pelo site.</p>
        </div>
        <div className="crm-overview-total" aria-label="Total de cadastros">
          <span>Total de cadastros</span>
          <strong>{total ?? '—'}</strong>
        </div>
      </div>

      <section className="crm-overview-summary" aria-label="Cadastros por status" aria-busy={loading}>
        {leadStatuses.map((status) => (
          <Link
            key={status}
            to={`/admin/cadastros?status=${status}`}
            className="crm-overview-summary-link"
            aria-label={`${statusLabels[status]}: ${data ? data.counts[status] : 'carregando'} cadastros`}
          >
            <span className="crm-overview-summary-label">
              <span className={`crm-overview-status-dot crm-overview-status-dot--${status}`} aria-hidden="true" />
              {statusLabels[status]}
            </span>
            <strong>{data ? data.counts[status] : '—'}</strong>
          </Link>
        ))}
      </section>

      <section className="crm-overview-recent" aria-labelledby="crm-recent-title" aria-busy={loading}>
        <div className="crm-overview-recent-heading">
          <h2 id="crm-recent-title">Cadastros recentes</h2>
          <Link className="crm-overview-view-all" to="/admin/cadastros">
            Ver todos <AdminIcon name="chevron-right" />
          </Link>
        </div>
        {loading ? (
          <div className="crm-overview-state" role="status">Carregando cadastros…</div>
        ) : error ? (
          <div className="crm-overview-state">
            <p className="crm-overview-error" role="alert">{error}</p>
            <button className="crm-overview-retry" type="button" onClick={() => setRetry((value) => value + 1)}>
              Tentar novamente
            </button>
          </div>
        ) : data?.items.length ? (
          <div className="crm-overview-table-wrap">
            <table className="crm-overview-table">
              <thead>
                <tr>
                  <th scope="col">Contato</th>
                  <th scope="col">Objetivo</th>
                  <th scope="col">Status</th>
                  <th scope="col">Recebido em</th>
                </tr>
              </thead>
              <tbody>
                {data.items.slice(0, 5).map((lead) => (
                  <tr key={lead.id}>
                    <td>
                      <div className="crm-overview-contact">
                        <span className="crm-overview-contact-avatar" aria-hidden="true">
                          {lead.name.trim().slice(0, 1).toLocaleUpperCase('pt-BR')}
                        </span>
                        <span className="crm-overview-contact-details">
                          <strong>{lead.name}</strong>
                          <span>{lead.email}</span>
                        </span>
                      </div>
                    </td>
                    <td><span className="crm-overview-objective" title={lead.objective}>{lead.objective}</span></td>
                    <td>
                      <span className="crm-overview-status">
                        <span className={`crm-overview-status-dot crm-overview-status-dot--${lead.status}`} aria-hidden="true" />
                        {statusLabels[lead.status]}
                      </span>
                    </td>
                    <td className="crm-overview-date">{formatAdminDate(lead.createdAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : data ? (
          <div className="crm-overview-state">
            <AdminIcon name="contacts" />
            <h3>Nenhum cadastro recebido</h3>
            <p>Os contatos recebidos pelo site aparecerão aqui.</p>
          </div>
        ) : null}
      </section>
    </div>
  )
}
