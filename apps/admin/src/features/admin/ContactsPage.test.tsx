// @vitest-environment jsdom
import { useState } from 'react'
import { afterEach, expect, it } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { Link, MemoryRouter } from 'react-router-dom'
import { ContactsPage } from './ContactsPage'
import type { AdminRequest } from './admin-api'
import type { LeadDraft } from './LeadPanel'
import type { AdminLead, LeadDetail, LeadList } from '@silent-voice/contracts/leads'

const lead: AdminLead = {
  id: 'lead-1',
  name: 'Ana Souza',
  email: 'ana@example.test',
  objective: 'Conhecer o dispositivo',
  status: 'new',
  version: 1,
  createdAt: '2026-10-15T12:00:00Z',
  updatedAt: '2026-10-15T12:00:00Z',
  duplicateEmail: false,
}
function list(items: AdminLead[], total = items.length): LeadList {
  return { items, total, page: 1, counts: { new: total, contacted: 0, demo_scheduled: 0, closed: 0 } }
}
function mount(request: AdminRequest, path = '/admin/cadastros') {
  function Harness() {
    const [drafts, setDrafts] = useState<Record<string, LeadDraft>>({})
    return <>
      <Link to="/admin/cadastros?status=contacted">Em contato na navegação</Link>
      <ContactsPage
        request={request}
        drafts={drafts}
        updateDraft={(id, update) => setDrafts((previous) => ({ ...previous, [id]: { ...(previous[id] ?? { text: '' }), ...update } }))}
      />
    </>
  }
  return render(<MemoryRouter initialEntries={[path]}><Harness /></MemoryRouter>)
}
afterEach(cleanup)

it('closes date filters with Escape while the toggle still has keyboard focus', async () => {
  mount((async () => list([lead])) as AdminRequest)
  await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
  const toggle = screen.getByRole('button', { name: 'Filtros' })
  toggle.focus()
  fireEvent.click(toggle)
  expect(screen.getByLabelText('De')).toBeInTheDocument()
  fireEvent.keyDown(toggle, { key: 'Escape' })
  expect(screen.queryByLabelText('De')).not.toBeInTheDocument()
  expect(toggle).toHaveFocus()
})

it('reapplies sidebar status navigation while the contacts page stays mounted', async () => {
  const request = (async (path: string) => {
    const status = new URL(path, 'https://example.test').searchParams.get('status')
    return list([{ ...lead, name: status === 'contacted' ? 'Bruno em contato' : 'Ana nova' }])
  }) as AdminRequest
  mount(request, '/admin/cadastros?status=new')
  expect(await screen.findByRole('button', { name: 'Ver contato de Ana nova' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: 'Em contato na navegação' }))
  expect(await screen.findByRole('button', { name: 'Ver contato de Bruno em contato' })).toBeInTheDocument()
  expect(screen.getByLabelText('Status')).toHaveValue('contacted')
})

it('ignores a late list response after search changes and preserves date filters for pagination', async () => {
  let completeOld: ((value: LeadList) => void) | undefined
  let oldSignal: AbortSignal | null | undefined
  const request = (async (path: string, options?: RequestInit) => {
    const params = new URL(path, 'https://example.test').searchParams
    if (!params.has('q')) {
      oldSignal = options?.signal
      return new Promise<LeadList>((resolve) => { completeOld = resolve })
    }
    if (params.get('from') !== '2026-10-01' || params.get('to') !== '2026-10-15') return list([])
    return list([{ ...lead, name: params.get('page') === '2' ? 'Segunda página' : 'Resultado atual' }], 26)
  }) as AdminRequest
  mount(request)
  await waitFor(() => expect(completeOld).toBeDefined())
  fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'Atual' } })
  fireEvent.click(screen.getByRole('button', { name: 'Filtros' }))
  fireEvent.change(screen.getByLabelText('De'), { target: { value: '2026-10-01' } })
  fireEvent.change(screen.getByLabelText('Até'), { target: { value: '2026-10-15' } })
  fireEvent.click(screen.getByRole('button', { name: 'Filtrar' }))
  expect(await screen.findByRole('button', { name: 'Ver contato de Resultado atual' })).toBeInTheDocument()
  expect(oldSignal?.aborted).toBe(true)
  await act(async () => { completeOld!(list([{ ...lead, name: 'Resposta antiga' }])) })
  expect(screen.queryByRole('button', { name: 'Ver contato de Resposta antiga' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Próxima →' }))
  expect(await screen.findByRole('button', { name: 'Ver contato de Segunda página' })).toBeInTheDocument()
  expect(screen.getByText('26–26 de 26 contatos')).toBeInTheDocument()
})

it('returns to page one and restores focus to the list when a status edit removes the current row', async () => {
  let changed = false
  const request = (async (path: string, options?: RequestInit) => {
    if (path === '/admin/leads/lead-1' && options?.method === 'PATCH') {
      changed = true
      return { ...lead, status: 'contacted', version: 2 }
    }
    if (path === '/admin/leads/lead-1') return { lead, notes: [] } satisfies LeadDetail
    const page = new URL(path, 'https://example.test').searchParams.get('page')
    return list(page === '2' ? [lead] : [{ ...lead, id: 'first', name: 'Primeira página' }], changed ? 25 : 26)
  }) as AdminRequest
  mount(request, '/admin/cadastros?status=new')
  await screen.findByRole('button', { name: 'Ver contato de Primeira página' })
  fireEvent.click(screen.getByRole('button', { name: 'Próxima →' }))
  const original = await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
  original.focus()
  fireEvent.click(original)
  fireEvent.change(await screen.findByLabelText('Status do contato'), { target: { value: 'contacted' } })
  fireEvent.click(screen.getByRole('button', { name: 'Salvar status' }))
  await screen.findByText('Status atualizado.')
  await screen.findByText('1–25 de 25 contatos')
  fireEvent.keyDown(screen.getByRole('button', { name: 'Fechar detalhes' }), { key: 'Escape' })
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Todos os contatos 25' })).toHaveFocus()
})

it('returns focus to the filters toggle after applying dates from the popover', async () => {
  mount((async () => list([lead])) as AdminRequest)
  await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
  const toggle = screen.getByRole('button', { name: 'Filtros' })
  fireEvent.click(toggle)
  fireEvent.change(screen.getByLabelText('De'), { target: { value: '2026-10-01' } })
  const apply = screen.getByRole('button', { name: 'Filtrar' })
  apply.focus()
  fireEvent.click(apply)
  expect(screen.queryByLabelText('De')).not.toBeInTheDocument()
  expect(toggle).toHaveFocus()
})

it('preserves search focus when submitting with the filters popover open', async () => {
  mount((async () => list([lead])) as AdminRequest)
  await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
  fireEvent.click(screen.getByRole('button', { name: 'Filtros' }))
  const search = screen.getByLabelText('Buscar')
  fireEvent.change(search, { target: { value: 'Ana' } })
  search.focus()
  fireEvent.submit(screen.getByRole('form', { name: 'Filtrar contatos' }))
  expect(screen.queryByLabelText('De')).not.toBeInTheDocument()
  expect(search).toHaveFocus()
})

it('returns focus to search when clearing the active filters removes its button', async () => {
  mount((async () => list([lead])) as AdminRequest, '/admin/cadastros?status=new')
  await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
  const clear = screen.getByRole('button', { name: 'Limpar filtros' })
  clear.focus()
  fireEvent.click(clear)
  expect(screen.queryByRole('button', { name: 'Limpar filtros' })).not.toBeInTheDocument()
  expect(screen.getByLabelText('Buscar')).toHaveFocus()
})
