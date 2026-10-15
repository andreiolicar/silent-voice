import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { leadStatuses, statusLabels } from '../../../shared/leads'
import type { LeadStatus } from '../../../shared/leads'
import { Brand } from '../../components/Brand'
import { AdminIcon } from './AdminIcon'
import './admin-layout.css'

type AdminLayoutProps = {
  children: ReactNode
  email: string
  onLogout: () => void
  loggingOut: boolean
  logoutError?: string
}

const statusIcons = {
  new: 'status-new',
  contacted: 'status-contacted',
  demo_scheduled: 'status-demo',
  closed: 'status-closed',
} as const

export function AdminLayout({
  children,
  email,
  onLogout,
  loggingOut,
  logoutError,
}: AdminLayoutProps) {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const requestedStatus = new URLSearchParams(location.search).get('status')
  const activeStatus = leadStatuses.includes(requestedStatus as LeadStatus)
    ? requestedStatus
    : null
  const contactsPage = location.pathname === '/admin/cadastros'
  const pageName = contactsPage ? 'Cadastros' : 'Visão geral'
  const initial = email.trim().slice(0, 1).toLocaleUpperCase('pt-BR') || 'S'
  const toggleLabel = collapsed ? 'Expandir menu' : 'Recolher menu'

  return (
    <div className={`crm-layout${collapsed ? ' crm-layout--collapsed' : ''}`}>
      <a className="crm-layout-skip" href="#admin-content">
        Ir para o conteúdo
      </a>
      <aside className="crm-layout-sidebar" aria-label="Menu principal">
        <div className="crm-layout-brand-row">
          {!collapsed && <Brand href="/" size="small" />}
          <button
            type="button"
            className="crm-layout-collapse"
            aria-label={toggleLabel}
            title={toggleLabel}
            aria-expanded={!collapsed}
            aria-controls="admin-sidebar-navigation"
            onClick={() => setCollapsed((value) => !value)}
          >
            <AdminIcon name={collapsed ? 'expand' : 'collapse'} />
          </button>
        </div>
        <nav
          className="crm-layout-navigation"
          id="admin-sidebar-navigation"
          aria-label="Navegação administrativa"
        >
          <div className="crm-nav-group">
            <p className="crm-nav-group-label">Geral</p>
            <Link
              className="crm-nav-link"
              to="/admin"
              aria-label="Visão geral"
              aria-current={!contactsPage ? 'page' : undefined}
              title={collapsed ? 'Visão geral' : undefined}
            >
              <AdminIcon name="overview" />
              <span className="crm-nav-label">Visão geral</span>
            </Link>
          </div>
          <div className="crm-nav-group">
            <p className="crm-nav-group-label">Registros</p>
            <Link
              className="crm-nav-link"
              to="/admin/cadastros"
              aria-label="Cadastros"
              aria-current={contactsPage && !activeStatus ? 'page' : undefined}
              title={collapsed ? 'Cadastros' : undefined}
            >
              <AdminIcon name="contacts" />
              <span className="crm-nav-label">Cadastros</span>
            </Link>
          </div>
          <div className="crm-nav-group crm-nav-group--statuses">
            <p className="crm-nav-group-label">Acompanhamento</p>
            {leadStatuses.map((status) => (
              <Link
                key={status}
                className="crm-nav-link"
                to={`/admin/cadastros?status=${status}`}
                aria-label={statusLabels[status]}
                aria-current={contactsPage && activeStatus === status ? 'page' : undefined}
                title={collapsed ? statusLabels[status] : undefined}
              >
                <AdminIcon name={statusIcons[status]} />
                <span className="crm-nav-label">{statusLabels[status]}</span>
              </Link>
            ))}
          </div>
        </nav>
        <div className="crm-layout-account">
          <div className="crm-layout-account-identity" title={email}>
            <span className="crm-layout-avatar" aria-hidden="true">{initial}</span>
            <span className="crm-layout-email">{email}</span>
          </div>
          <button
            type="button"
            className="crm-layout-logout"
            onClick={onLogout}
            disabled={loggingOut}
            aria-label={loggingOut ? 'Saindo…' : 'Sair'}
            title={collapsed ? (loggingOut ? 'Saindo…' : 'Sair') : undefined}
          >
            <AdminIcon name="logout" />
            <span className="crm-layout-logout-label">{loggingOut ? 'Saindo…' : 'Sair'}</span>
          </button>
        </div>
      </aside>
      <div className="crm-layout-workspace">
        <header className="crm-layout-topbar">
          <nav className="crm-layout-breadcrumb" aria-label="Localização atual">
            <span className="crm-layout-breadcrumb-parent">{contactsPage ? 'Registros' : 'Geral'}</span>
            <AdminIcon name="chevron-right" />
            <span className="crm-layout-current-page" aria-current="page">
              <AdminIcon name={contactsPage ? 'contacts' : 'overview'} />
              <span>{pageName}</span>
            </span>
          </nav>
          <span className="crm-layout-topbar-avatar" title={email} aria-label={`Conta: ${email}`}>
            {initial}
          </span>
        </header>
        {logoutError && <p className="crm-layout-error" role="alert">{logoutError}</p>}
        <main className="crm-layout-content" id="admin-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  )
}
