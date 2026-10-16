// @vitest-environment jsdom
import { afterEach, expect, it } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { ContactsPage } from './ContactsPage'
import type { AdminRequest } from './admin-api'
import type { AdminLead, LeadList, LeadStatus } from '../../../shared/leads'

const counts: LeadList['counts'] = { new: 14, contacted: 8, demo_scheduled: 32, closed: 5 }
const stages = [
  { status: 'new', label: 'Novo', count: 14, name: 'Ana nova' },
  { status: 'contacted', label: 'Em contato', count: 8, name: 'Bruno em contato' },
  { status: 'demo_scheduled', label: 'Demonstração combinada', count: 32, name: 'Carla demonstração' },
  { status: 'closed', label: 'Encerrado', count: 5, name: 'Diego encerrado' },
] as const

function contact(status: LeadStatus = 'new', name = 'Ana nova', id = `lead-${status}`): AdminLead {
  return {
    id,
    name,
    email: `${id}@example.test`,
    objective: 'Conhecer o dispositivo',
    status,
    version: 1,
    createdAt: '2026-10-15T12:00:00Z',
    updatedAt: '2026-10-15T12:00:00Z',
    duplicateEmail: false,
  }
}

function list(items: AdminLead[], total = items.length, page = 1): LeadList {
  return { items, total, page, counts }
}

function fakeRequest(resolve: (url: URL) => LeadList | Promise<LeadList>) {
  const paths: URL[] = []
  const request = (async (path: string) => {
    const url = new URL(path, 'https://example.test')
    paths.push(url)
    return resolve(url)
  }) as AdminRequest
  return { request, paths }
}

function mount(request: AdminRequest, path = '/admin/acompanhamento') {
  function Harness() {
    const location = useLocation()
    const navigate = useNavigate()
    return <>
      <button type="button" onClick={() => navigate(-1)}>Voltar no histórico</button>
      <output aria-label="Rota atual">{location.pathname}{location.search}</output>
      <ContactsPage view="tracking" request={request} drafts={{}} updateDraft={() => {}} />
    </>
  }
  return render(<MemoryRouter initialEntries={[path]}><Harness /></MemoryRouter>)
}

function applySearchAndDates(query: string) {
  fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: query } })
  fireEvent.click(screen.getByRole('button', { name: 'Filtros' }))
  fireEvent.change(screen.getByLabelText('De'), { target: { value: '2026-10-01' } })
  fireEvent.change(screen.getByLabelText('Até'), { target: { value: '2026-10-15' } })
  fireEvent.click(screen.getByRole('button', { name: 'Filtrar' }))
}

afterEach(cleanup)

it('defaults missing and invalid tracking statuses to new without a duplicate status selector', async () => {
  for (const path of ['/admin/acompanhamento', '/admin/acompanhamento?status=invalid']) {
    const { request, paths } = fakeRequest(() => list([contact()]))
    const view = mount(request, path)
    await screen.findByRole('button', { name: 'Ver contato de Ana nova' })
    const navigation = screen.getByRole('navigation', { name: 'Status do acompanhamento' })
    expect(within(navigation).getAllByRole('link')).toHaveLength(4)
    expect(within(navigation).getByRole('link', { name: 'Novo: 14 contatos' })).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('combobox', { name: 'Status' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Acompanhamento de contatos 1' })).toBeInTheDocument()
    expect(paths.at(-1)?.pathname).toBe('/admin/leads')
    expect(paths.at(-1)?.searchParams.get('status')).toBe('new')
    expect(paths.at(-1)?.searchParams.get('page')).toBe('1')
    view.unmount()
  }
})

it('navigates all four status links and browser history while preserving applied search and dates', async () => {
  const { request, paths } = fakeRequest((url) => {
    const stage = stages.find((item) => item.status === url.searchParams.get('status'))
    return list(stage ? [contact(stage.status, stage.name)] : [])
  })
  mount(request, '/admin/acompanhamento?status=new')
  await screen.findByRole('button', { name: 'Ver contato de Ana nova' })
  applySearchAndDates('Equipe')
  await waitFor(() => expect(paths.at(-1)?.searchParams.get('q')).toBe('Equipe'))

  const navigation = screen.getByRole('navigation', { name: 'Status do acompanhamento' })
  for (const stage of stages) {
    expect(within(navigation).getByRole('link', { name: `${stage.label}: ${stage.count} contatos` }))
      .toHaveAttribute('href', `/admin/acompanhamento?status=${stage.status}`)
  }

  for (const stage of [stages[1], stages[2], stages[3], stages[0]]) {
    fireEvent.click(within(navigation).getByRole('link', { name: `${stage.label}: ${stage.count} contatos` }))
    await screen.findByRole('button', { name: `Ver contato de ${stage.name}` })
    expect(screen.getByLabelText('Rota atual')).toHaveTextContent(`/admin/acompanhamento?status=${stage.status}`)
    expect(within(navigation).getByRole('link', { name: `${stage.label}: ${stage.count} contatos` })).toHaveAttribute('aria-current', 'page')
    expect(within(navigation).getAllByRole('link').filter((link) => link.getAttribute('aria-current') === 'page')).toHaveLength(1)
    expect(paths.at(-1)?.pathname).toBe('/admin/leads')
    expect(Object.fromEntries(paths.at(-1)!.searchParams)).toEqual({
      page: '1', q: 'Equipe', status: stage.status, from: '2026-10-01', to: '2026-10-15',
    })
  }

  fireEvent.click(screen.getByRole('button', { name: 'Voltar no histórico' }))
  await screen.findByRole('button', { name: 'Ver contato de Diego encerrado' })
  expect(within(navigation).getByRole('link', { name: 'Encerrado: 5 contatos' })).toHaveAttribute('aria-current', 'page')
  expect(paths.at(-1)?.searchParams.get('status')).toBe('closed')
  expect(paths.at(-1)?.searchParams.get('q')).toBe('Equipe')
  expect(screen.getByLabelText('Buscar')).toHaveValue('Equipe')
  fireEvent.click(screen.getByRole('button', { name: 'Filtros' }))
  expect(screen.getByLabelText('De')).toHaveValue('2026-10-01')
  expect(screen.getByLabelText('Até')).toHaveValue('2026-10-15')
})

it('clears search and dates from page two while retaining the tracking status and returning focus to search', async () => {
  const { request, paths } = fakeRequest((url) => {
    const page = Number(url.searchParams.get('page'))
    if (!url.searchParams.has('q')) return list([contact('demo_scheduled', 'Sem filtros de busca')])
    const items = page === 2
      ? [contact('demo_scheduled', 'Silva na segunda página', 'silva-26')]
      : Array.from({ length: 25 }, (_, index) => contact('demo_scheduled', `Silva ${index + 1}`, `silva-${index + 1}`))
    return list(items, 26, page)
  })
  mount(request, '/admin/acompanhamento?status=demo_scheduled')
  await screen.findByRole('button', { name: 'Ver contato de Sem filtros de busca' })
  applySearchAndDates('Silva')
  await screen.findByRole('button', { name: 'Ver contato de Silva 1' })
  fireEvent.click(screen.getByRole('button', { name: 'Próxima →' }))
  await screen.findByRole('button', { name: 'Ver contato de Silva na segunda página' })
  expect(screen.getByText('26–26 de 26 contatos')).toBeInTheDocument()

  const clear = screen.getByRole('button', { name: 'Limpar filtros' })
  clear.focus()
  fireEvent.click(clear)
  await screen.findByRole('button', { name: 'Ver contato de Sem filtros de busca' })
  expect(Object.fromEntries(paths.at(-1)!.searchParams)).toEqual({ page: '1', status: 'demo_scheduled' })
  expect(screen.getByLabelText('Rota atual')).toHaveTextContent('/admin/acompanhamento?status=demo_scheduled')
  expect(screen.getByRole('link', { name: 'Demonstração combinada: 32 contatos' })).toHaveAttribute('aria-current', 'page')
  expect(screen.getByLabelText('Buscar')).toHaveValue('')
  expect(screen.getByLabelText('Buscar')).toHaveFocus()
  expect(screen.queryByRole('button', { name: 'Limpar filtros' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: '← Anterior' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Filtros' }))
  expect(screen.getByLabelText('De')).toHaveValue('')
  expect(screen.getByLabelText('Até')).toHaveValue('')
})

it('announces loading counts then displays global status counts independently of the filtered total', async () => {
  let complete: ((value: LeadList) => void) | undefined
  const { request } = fakeRequest(() => new Promise<LeadList>((resolve) => { complete = resolve }))
  mount(request, '/admin/acompanhamento?status=new')
  const navigation = screen.getByRole('navigation', { name: 'Status do acompanhamento' })
  for (const stage of stages) {
    expect(within(navigation).getByRole('link', { name: `${stage.label}: carregando contatos` })).toBeInTheDocument()
  }
  await act(async () => {
    complete!({ items: [contact()], total: 1, page: 1, counts: { new: 12, contacted: 0, demo_scheduled: 8, closed: 3 } })
  })
  expect(within(navigation).getByRole('link', { name: 'Novo: 12 contatos' })).toHaveAttribute('aria-current', 'page')
  expect(within(navigation).getByRole('link', { name: 'Em contato: 0 contatos' })).toBeInTheDocument()
  expect(within(navigation).getByRole('link', { name: 'Demonstração combinada: 8 contatos' })).toBeInTheDocument()
  expect(within(navigation).getByRole('link', { name: 'Encerrado: 3 contatos' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Acompanhamento de contatos 1' })).toBeInTheDocument()
  expect(screen.getByText('1–1 de 1 contatos')).toBeInTheDocument()
})
