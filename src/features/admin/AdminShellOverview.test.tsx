// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router-dom'
import type { LeadList } from '../../../shared/leads'
import type { AdminRequest } from './admin-api'
import { AdminLayout } from './AdminLayout'
import { Overview } from './Overview'

const leads: LeadList = {
  items: Array.from({ length: 6 }, (_, index) => ({
    id: `lead-${index}`,
    name: `Contato ${index + 1}`,
    email: `contato${index + 1}@example.com`,
    objective: 'Conhecer o dispositivo',
    status: 'new',
    version: 1,
    createdAt: '2026-10-15T12:00:00.000Z',
    updatedAt: '2026-10-15T12:00:00.000Z',
    duplicateEmail: false,
  })),
  total: 6,
  page: 1,
  counts: { new: 6, contacted: 3, demo_scheduled: 2, closed: 1 },
}
const requestFor = (value: LeadList): AdminRequest =>
  async <T,>() => value as T

afterEach(cleanup)

describe('administrative shell', () => {
  it('groups all tracking statuses under one sidebar item and supports collapsing the menu', () => {
    render(
      <MemoryRouter initialEntries={['/admin/acompanhamento?status=contacted']}>
        <AdminLayout
          email="gestao@example.com"
          onLogout={() => undefined}
          loggingOut={false}
        >
          <h1>Conteúdo</h1>
        </AdminLayout>
      </MemoryRouter>
    )
    const navigation = screen.getByRole('navigation', { name: 'Navegação administrativa' })
    expect(within(navigation).getByRole('link', { name: 'Acompanhamento' })).toHaveAttribute('aria-current', 'page')
    expect(within(navigation).getByRole('link', { name: 'Cadastros' })).not.toHaveAttribute('aria-current')
    expect(within(navigation).getAllByRole('link')).toHaveLength(3)
    expect(within(navigation).queryByRole('link', { name: 'Novo' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Recolher menu' }))
    expect(screen.getByRole('button', { name: 'Expandir menu' })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('heading', { name: 'Conteúdo' })).toBeVisible()
    expect(within(navigation).getByRole('link', { name: 'Acompanhamento' })).toHaveAttribute('href', '/admin/acompanhamento')
  })

  it('shows the account and the current logout state', () => {
    const logout = vi.fn()
    render(
      <MemoryRouter>
        <AdminLayout email="gestao@example.com" onLogout={logout} loggingOut logoutError="Tente novamente.">
          Conteúdo
        </AdminLayout>
      </MemoryRouter>
    )
    expect(screen.getByText('gestao@example.com')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Saindo…' })).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent('Tente novamente.')
  })
})

describe('administrative overview', () => {
  it('uses global status counts and shows only the five most recent records', async () => {
    render(<MemoryRouter><Overview request={requestFor(leads)} /></MemoryRouter>)
    expect(await screen.findByText('Contato 1')).toBeVisible()
    expect(screen.getByText('Contato 5')).toBeVisible()
    expect(screen.queryByText('Contato 6')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Total de cadastros')).toHaveTextContent('12')
    expect(screen.getByRole('link', { name: 'Em contato: 3 cadastros' })).toHaveAttribute('href', '/admin/acompanhamento?status=contacted')
  })

  it('shows a real empty state for an empty list', async () => {
    const empty = { ...leads, items: [], total: 0, counts: { new: 0, contacted: 0, demo_scheduled: 0, closed: 0 } }
    render(<MemoryRouter><Overview request={requestFor(empty)} /></MemoryRouter>)
    expect(await screen.findByText('Nenhum cadastro recebido')).toBeVisible()
    expect(screen.getByLabelText('Total de cadastros')).toHaveTextContent('0')
  })

  it('retries loading after a request failure without showing an empty state', async () => {
    let attempts = 0
    const request: AdminRequest = async <T,>() => {
      attempts += 1
      if (attempts === 1) throw new Error('offline')
      return leads as T
    }
    render(<MemoryRouter><Overview request={request} /></MemoryRouter>)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível concluir')
    expect(screen.queryByText('Nenhum cadastro recebido')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(await screen.findByText('Contato 1')).toBeVisible()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
