// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router-dom'
import { AdminApp } from './AdminApp'

const lead = {
  id: 'lead-1',
  name: 'Ana Souza',
  email: 'ana@example.com',
  objective: 'Conhecer o dispositivo',
  profile: 'self',
  status: 'new',
  version: 1,
  createdAt: '2026-10-15T12:00:00.000Z',
  updatedAt: '2026-10-15T12:00:00.000Z',
  duplicateEmail: true,
}
const counts = { new: 1, contacted: 0, demo_scheduled: 0, closed: 0 }
const response = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
function setupFetch(
  overrides: (
    path: string,
    init?: RequestInit
  ) => Response | Promise<Response> | undefined = () => undefined
) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const path = String(input)
      const overridden = overrides(path, init)
      if (overridden) return overridden
      if (path === '/api/auth/csrf')
        return response({ csrfToken: 'csrf-value' })
      if (path === '/api/auth/session')
        return response({
          user: { email: 'admin@example.com' },
          csrfToken: 'csrf-value',
        })
      if (path === '/api/auth/login') {
        if (
          init?.headers &&
          new Headers(init.headers).get('X-CSRF-Token') === 'csrf-value'
        )
          return response({
            user: { email: 'admin@example.com' },
            csrfToken: 'next-csrf',
          })
        return response({ error: 'CSRF_INVALID' }, 403)
      }
      if (path === '/api/admin/leads/lead-1')
        return response({ lead, notes: [] })
      if (path.startsWith('/api/admin/leads?'))
        return response({ items: [lead], total: 1, page: 1, counts })
      return response({ error: 'NOT_FOUND' }, 404)
    })
  )
}
function mount(path = '/admin/cadastros') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AdminApp />
    </MemoryRouter>
  )
}
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('administrative workflow', () => {
  it('opens the overview first and navigates to the contact register through the sidebar', async () => {
    setupFetch()
    mount('/admin')
    expect(await screen.findByRole('heading', { name: 'Visão geral' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Buscar')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Cadastros' }))
    expect(await screen.findByLabelText('Buscar')).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })).toBeInTheDocument()
  })

  it('logs in with CSRF and renders actual empty state', async () => {
    setupFetch((path) =>
      path.startsWith('/api/admin/leads?')
        ? response({
            items: [],
            total: 0,
            page: 1,
            counts: { new: 0, contacted: 0, demo_scheduled: 0, closed: 0 },
          })
        : undefined
    )
    mount('/admin/login')
    fireEvent.change(await screen.findByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(
      await screen.findByText('Nenhum cadastro recebido')
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sair' })).toBeInTheDocument()
  })

  it('shows lead details, preserves a note draft after version conflict and can save it', async () => {
    let savedNote = false
    setupFetch((path, init) => {
      if (path === '/api/admin/leads/lead-1' && init?.method === 'PATCH')
        return response({ error: 'VERSION_CONFLICT' }, 409)
      if (path === '/api/admin/leads/lead-1/notes' && init?.method === 'POST') {
        if (
          JSON.parse(String(init.body)).text !== 'Ligar amanhã' ||
          new Headers(init.headers).get('X-CSRF-Token') !== 'csrf-value'
        )
          return response({}, 400)
        savedNote = true
        return response(
          {
            id: 'note-1',
            text: 'Ligar amanhã',
            author: 'admin@example.com',
            createdAt: '2026-10-15T13:00:00.000Z',
          },
          201
        )
      }
      if (path === '/api/admin/leads/lead-1')
        return response({
          lead,
          notes: savedNote
            ? [
                {
                  id: 'note-1',
                  text: 'Ligar amanhã',
                  author: 'admin@example.com',
                  createdAt: '2026-10-15T13:00:00.000Z',
                },
              ]
            : [],
        })
    })
    mount()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    const panel = await screen.findByRole('dialog', {
      name: 'Contato de Ana Souza',
    })
    expect(within(panel).getByText('E-mail repetido')).toBeInTheDocument()
    fireEvent.change(within(panel).getByLabelText('Nova anotação'), {
      target: { value: 'Ligar amanhã' },
    })
    fireEvent.change(within(panel).getByLabelText('Status do contato'), {
      target: { value: 'contacted' },
    })
    fireEvent.click(
      within(panel).getByRole('button', { name: 'Salvar status' })
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'atualizado por outra pessoa'
    )
    expect(within(panel).getByLabelText('Nova anotação')).toHaveValue(
      'Ligar amanhã'
    )
    fireEvent.click(
      within(panel).getByRole('button', { name: 'Adicionar anotação' })
    )
    await waitFor(() =>
      expect(within(panel).getByLabelText('Nova anotação')).toHaveValue('')
    )
    expect(within(panel).getByText('Ligar amanhã')).toBeInTheDocument()
  })

  it('removes private details on session expiry and restores the in-memory note after login', async () => {
    let expired = false
    setupFetch((path) => {
      if (path === '/api/admin/leads/lead-1/notes') {
        expired = true
        return response({}, 401)
      }
      if (path === '/api/auth/session' && expired) return response({}, 401)
      if (path === '/api/auth/login') {
        expired = false
        return response({
          user: { email: 'admin@example.com' },
          csrfToken: 'new-token',
        })
      }
    })
    mount()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    fireEvent.change(await screen.findByLabelText('Nova anotação'), {
      target: { value: 'Rascunho protegido' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Adicionar anotação' }))
    expect(await screen.findByLabelText('Senha')).toBeInTheDocument()
    expect(screen.queryByText('ana@example.com')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    fireEvent.click(await screen.findByRole('link', { name: 'Cadastros' }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    expect(await screen.findByLabelText('Nova anotação')).toHaveValue(
      'Rascunho protegido'
    )
  })
  it('announces invalid credentials and clears the password for another attempt', async () => {
    setupFetch((path) =>
      path === '/api/auth/login' ? response({}, 401) : undefined
    )
    mount('/admin/login')
    fireEvent.change(await screen.findByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'wrong-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'E-mail ou senha incorretos'
    )
    expect(screen.getByLabelText('Senha')).toHaveValue('')
    await waitFor(() => expect(screen.getByLabelText('Senha')).toHaveFocus())
    expect(screen.getByLabelText('Senha')).toHaveAttribute(
      'aria-invalid',
      'true'
    )
    expect(screen.getByLabelText('Senha')).toHaveAccessibleDescription(
      'E-mail ou senha incorretos. Tente novamente.'
    )
  })

  it('keeps a retry target focused after a login service error without marking credentials invalid', async () => {
    setupFetch((path) =>
      path === '/api/auth/login' ? response({}, 503) : undefined
    )
    mount('/admin/login')
    fireEvent.change(await screen.findByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível concluir'
    )
    await waitFor(() => expect(screen.getByLabelText('Senha')).toHaveFocus())
    expect(screen.getByLabelText('Senha')).not.toHaveAttribute(
      'aria-invalid',
      'true'
    )
  })

  it('retries a failed list request and displays only the returned records', async () => {
    let failed = true
    setupFetch((path) => {
      if (path.startsWith('/api/admin/leads?') && failed) {
        failed = false
        return response({}, 503)
      }
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível concluir'
    )
    expect(
      screen.queryByRole('button', { name: 'Ver contato de Ana Souza' })
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    ).toBeInTheDocument()
  })

  it('applies search, status, dates and page while retaining the real status counts', async () => {
    setupFetch((path) => {
      if (!path.startsWith('/api/admin/leads?')) return undefined
      const query = new URL(path, 'https://example.test').searchParams
      if (query.get('page') === '2')
        return response({
          items: [{ ...lead, id: 'lead-26', name: 'Bruno Lima' }],
          total: 26,
          page: 2,
          counts: { ...counts, contacted: 26 },
        })
      if (
        query.get('q') === 'Ana' &&
        query.get('status') === 'contacted' &&
        query.get('from') === '2026-10-01' &&
        query.get('to') === '2026-10-15'
      )
        return response({
          items: [{ ...lead, status: 'contacted' }],
          total: 26,
          page: 1,
          counts: { ...counts, contacted: 26 },
        })
      return response({ items: [lead], total: 1, page: 1, counts })
    })
    mount()
    await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    fireEvent.change(screen.getByLabelText('Buscar'), {
      target: { value: 'Ana' },
    })
    fireEvent.change(screen.getByLabelText('Status'), {
      target: { value: 'contacted' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Filtros' }))
    fireEvent.change(screen.getByLabelText('De'), {
      target: { value: '2026-10-01' },
    })
    fireEvent.change(screen.getByLabelText('Até'), {
      target: { value: '2026-10-15' },
    })
    fireEvent.submit(screen.getByRole('form', { name: 'Filtrar contatos' }))
    expect(await screen.findByText('1–25 de 26 contatos')).toBeInTheDocument()
    expect(screen.getByLabelText('Status')).toHaveValue('contacted')
    expect(screen.getByRole('link', { name: 'Em contato' })).toHaveAttribute('aria-current', 'page')
    fireEvent.click(screen.getByRole('button', { name: 'Próxima →' }))
    expect(
      await screen.findByRole('button', { name: 'Ver contato de Bruno Lima' })
    ).toBeInTheDocument()
    expect(screen.getByText('26–26 de 26 contatos')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Próxima →' })).toBeDisabled()
  })

  it('allows background navigation with inline details and returns focus after Escape', async () => {
    setupFetch()
    mount()
    const trigger = await screen.findByRole('button', {
      name: 'Ver contato de Ana Souza',
    })
    trigger.focus()
    fireEvent.click(trigger)
    const close = await screen.findByRole('button', {
      name: 'Fechar detalhes',
    })
    expect(close).toHaveFocus()
    fireEvent.change(await screen.findByLabelText('Nova anotação'), {
      target: { value: 'Um próximo passo' },
    })
    const save = screen.getByRole('button', { name: 'Adicionar anotação' })
    save.focus()
    fireEvent.keyDown(save, { key: 'Tab' })
    expect(save).toHaveFocus()
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'false')
    expect(screen.getByRole('link', { name: 'Cadastros' })).toBeInTheDocument()
    fireEvent.keyDown(close, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })
  it('aborts replaced list queries and prevents their late responses replacing current results', async () => {
    let completeOld: ((value: Response) => void) | undefined
    let oldSignal: AbortSignal | undefined
    setupFetch()
    const original = globalThis.fetch
    vi.stubGlobal(
      'fetch',
      async (input: string | URL | Request, init?: RequestInit) => {
        if (String(input) === '/api/admin/leads?page=1') {
          oldSignal = init?.signal ?? undefined
          return new Promise<Response>((resolve) => {
            completeOld = resolve
          })
        }
        return original(input, init)
      }
    )
    mount()
    await waitFor(() => expect(completeOld).toBeDefined())
    fireEvent.change(screen.getByLabelText('Buscar'), {
      target: { value: 'Atual' },
    })
    fireEvent.submit(screen.getByRole('form', { name: 'Filtrar contatos' }))
    expect(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    ).toBeInTheDocument()
    expect(oldSignal?.aborted).toBe(true)
    await act(async () => {
      completeOld!(
        response({
          items: [{ ...lead, name: 'Resposta antiga' }],
          total: 1,
          page: 1,
          counts,
        })
      )
    })
    await waitFor(() =>
      expect(
        screen.queryByRole('button', {
          name: 'Ver contato de Resposta antiga',
        })
      ).not.toBeInTheDocument()
    )
    expect(
      screen.getByRole('button', { name: 'Ver contato de Ana Souza' })
    ).toBeInTheDocument()
  })

  it('logs out with CSRF, removes private details and clears drafts before the next login', async () => {
    setupFetch((path, init) => {
      if (path === '/api/auth/logout')
        return new Headers(init?.headers).get('X-CSRF-Token') === 'csrf-value'
          ? response({ ok: true })
          : response({}, 403)
    })
    mount()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    fireEvent.change(await screen.findByLabelText('Nova anotação'), {
      target: { value: 'Rascunho anterior' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Fechar detalhes' }))
    fireEvent.click(screen.getByRole('button', { name: 'Sair' }))
    expect(await screen.findByLabelText('Senha')).toBeInTheDocument()
    expect(screen.queryByText('ana@example.com')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    fireEvent.click(await screen.findByRole('link', { name: 'Cadastros' }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    expect(await screen.findByLabelText('Nova anotação')).toHaveValue('')
  })
  it('returns to a valid first page when a status edit removes the last match on page two', async () => {
    let changed = false
    setupFetch((path, init) => {
      if (path === '/api/admin/leads/lead-1' && init?.method === 'PATCH') {
        changed = true
        return response({ ...lead, status: 'contacted', version: 2 })
      }
      if (path.startsWith('/api/admin/leads?')) {
        const page = Number(
          new URL(path, 'https://example.test').searchParams.get('page')
        )
        const firstPage = Array.from({ length: 25 }, (_, index) => ({
          ...lead,
          id: `first-${index}`,
          name:
            index === 0 ? 'Contato da primeira página' : `Contato ${index + 1}`,
        }))
        const items = page === 2 ? (changed ? [] : [lead]) : firstPage
        return response({
          items,
          total: changed ? 25 : 26,
          page,
          counts: {
            ...counts,
            new: changed ? 25 : 26,
            contacted: changed ? 1 : 0,
          },
        })
      }
    })
    mount()
    fireEvent.click(
      await screen.findByRole('link', { name: 'Novo' })
    )
    await screen.findByText('1–25 de 26 contatos')
    fireEvent.click(screen.getByRole('button', { name: 'Próxima →' }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    fireEvent.change(await screen.findByLabelText('Status do contato'), {
      target: { value: 'contacted' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar status' }))
    await screen.findByText('Status atualizado.')
    fireEvent.click(screen.getByRole('button', { name: 'Fechar detalhes' }))
    expect(await screen.findByText('1–25 de 25 contatos')).toBeInTheDocument()
    expect(
      screen.getByRole('button', {
        name: 'Ver contato de Contato da primeira página',
      })
    ).toBeInTheDocument()
    expect(
      screen.queryByText('Nenhum contato encontrado')
    ).not.toBeInTheDocument()
    expect(screen.getByText('Página 1')).toBeInTheDocument()
  })

  it.each([false, true])(
    'restores focus after status refresh when the lead is filtered out: %s',
    async (filteredOut) => {
      let changed = false
      let completeRefresh: (() => void) | undefined
      setupFetch((path, init) => {
        if (path === '/api/admin/leads/lead-1' && init?.method === 'PATCH') {
          changed = true
          return response({ ...lead, status: 'contacted', version: 2 })
        }
        if (path.startsWith('/api/admin/leads?')) {
          const items =
            changed && filteredOut
              ? []
              : [{ ...lead, status: changed ? 'contacted' : 'new' }]
          const result = response({
            items,
            total: items.length,
            page: 1,
            counts: {
              new: changed ? 0 : 1,
              contacted: changed ? 1 : 0,
              demo_scheduled: 0,
              closed: 0,
            },
          })
          return changed
            ? new Promise<Response>((resolve) => {
                completeRefresh = () => resolve(result)
              })
            : result
        }
      })
      mount()
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
      if (filteredOut) {
        fireEvent.click(
          screen.getByRole('link', { name: 'Novo' })
        )
        await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
      }
      const original = screen.getByRole('button', {
        name: 'Ver contato de Ana Souza',
      })
      original.focus()
      fireEvent.click(original)
      fireEvent.change(await screen.findByLabelText('Status do contato'), {
        target: { value: 'contacted' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Salvar status' }))
      await screen.findByText('Status atualizado.')
      await waitFor(() => {
        expect(completeRefresh).toBeDefined()
        expect(original.isConnected).toBe(false)
      })
      await act(async () => {
        completeRefresh!()
      })
      if (filteredOut) await screen.findByText('Nenhum contato encontrado')
      else
        await waitFor(() =>
          expect(
            within(screen.getByRole('table')).getByText('Em contato')
          ).toBeInTheDocument()
        )
      expect(original.isConnected).toBe(false)
      fireEvent.keyDown(
        screen.getByRole('button', { name: 'Fechar detalhes' }),
        { key: 'Escape' }
      )
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      if (filteredOut)
        expect(
          screen.getByRole('heading', { name: 'Todos os contatos 0' })
        ).toHaveFocus()
      else
        expect(
          screen.getByRole('button', { name: 'Ver contato de Ana Souza' })
        ).toHaveFocus()
    }
  )

  it('preserves an empty note draft when changing status before writing a note', async () => {
    setupFetch()
    mount()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    fireEvent.change(await screen.findByLabelText('Status do contato'), {
      target: { value: 'contacted' },
    })
    expect(screen.getByLabelText('Nova anotação')).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Salvar status' })).toBeEnabled()
  })
})
