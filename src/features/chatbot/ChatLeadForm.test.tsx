import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ChatLeadForm } from './ChatLeadForm'

const receipt = { id: 'lead-1', createdAt: '2026-10-15T12:00:00.000Z' }
async function fillForm() {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Nome'), 'Maria Silva')
  await user.type(screen.getByLabelText('E-mail'), 'maria@example.com')
  await user.type(
    screen.getByLabelText('Objetivo do contato'),
    'Quero conhecer o dispositivo.'
  )
  return user
}
afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})
describe('explicit lead registration', () => {
  it('associates local validation and only confirms a valid committed receipt', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(receipt), { status: 201 }))
    vi.stubGlobal('fetch', fetcher)
    render(<ChatLeadForm />)
    fireEvent.click(screen.getByRole('button', { name: 'Registrar interesse' }))
    expect(screen.getByLabelText('Nome')).toHaveAttribute(
      'aria-invalid',
      'true'
    )
    expect(fetcher).not.toHaveBeenCalled()
    const user = await fillForm()
    await user.click(
      screen.getByRole('button', { name: 'Registrar interesse' })
    )
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Seu interesse foi registrado'
    )
    expect(fetcher).toHaveBeenCalledWith(
      '/api/leads',
      expect.objectContaining({ method: 'POST' })
    )
    expect(
      screen.getByRole('link', { name: 'contato@silentvoice.com.br' })
    ).toHaveAttribute('href', 'mailto:contato@silentvoice.com.br')
  })
  it('treats a timeout as unknown and retries exactly the same immutable payload and key', async () => {
    const requests: RequestInit[] = []
    const fetcher = vi.fn((_url: string, init: RequestInit) => {
      requests.push(init)
      return requests.length === 1
        ? new Promise<Response>(() => {})
        : Promise.resolve(
            new Response(JSON.stringify(receipt), { status: 200 })
          )
    })
    vi.stubGlobal('fetch', fetcher)
    render(<ChatLeadForm />)
    await fillForm()
    vi.useFakeTimers()
    fireEvent.click(screen.getByRole('button', { name: 'Registrar interesse' }))
    expect(screen.getByLabelText('Nome')).toHaveAttribute('readonly')
    expect(screen.getByLabelText('Perfil (opcional)')).toBeDisabled()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15000)
    })
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível confirmar o registro'
    )
    expect(screen.queryByText('Seu interesse foi registrado')).toBeNull()
    fireEvent.click(
      screen.getByRole('button', { name: 'Tentar confirmar novamente' })
    )
    await act(async () => {})
    expect(screen.getByRole('status')).toHaveTextContent(
      'Seu interesse foi registrado'
    )
    expect(requests[1].body).toBe(requests[0].body)
    expect(requests[1].headers).toEqual(requests[0].headers)
    expect(
      (requests[0].headers as Record<string, string>)['Idempotency-Key']
    ).toMatch(/^[\da-f-]{36}$/)
  })
  it('does not confirm a success status with an invalid receipt and ignores results after unmount', async () => {
    let resolve!: (value: Response) => void
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise<Response>((r) => {
            resolve = r
          })
      )
    )
    const { unmount } = render(<ChatLeadForm />)
    const user = await fillForm()
    await user.click(
      screen.getByRole('button', { name: 'Registrar interesse' })
    )
    await act(async () => {
      resolve(new Response('{}', { status: 201 }))
    })
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível confirmar'
    )
    await user.click(
      screen.getByRole('button', { name: 'Tentar confirmar novamente' })
    )
    unmount()
    await act(async () => {
      resolve(new Response(JSON.stringify(receipt), { status: 201 }))
    })
    expect(screen.queryByText(/Seu interesse foi registrado/)).toBeNull()
  })
  it('rejects a blank receipt identifier even when the server returns 201', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ id: ' ', createdAt: '2026-10-15T12:00:00.000Z' }),
            { status: 201 }
          )
        )
    )
    render(<ChatLeadForm />)
    const user = await fillForm()
    await user.click(
      screen.getByRole('button', { name: 'Registrar interesse' })
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível confirmar'
    )
    expect(screen.queryByText(/Seu interesse foi registrado/)).toBeNull()
  })
  it.each([429, 403, 400, 422])('retains the same unknown submission through a retry rejected with %s', async status => {
    const fetcher=vi.fn().mockRejectedValueOnce(new Error('connection lost')).mockResolvedValueOnce(new Response('{}',{status})).mockResolvedValueOnce(new Response(JSON.stringify(receipt),{status:200}))
    vi.stubGlobal('fetch',fetcher)
    render(<ChatLeadForm/>)
    const user=await fillForm()
    await user.click(screen.getByRole('button',{name:'Registrar interesse'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível confirmar')
    await user.click(screen.getByRole('button',{name:'Tentar confirmar novamente'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível confirmar')
    expect(screen.getByLabelText('Nome')).toHaveAttribute('readonly')
    expect(screen.getByLabelText('Perfil (opcional)')).toBeDisabled()
    await user.click(screen.getByRole('button',{name:'Tentar confirmar novamente'}))
    expect(await screen.findByRole('status')).toHaveTextContent('Seu interesse foi registrado')
    const requests=fetcher.mock.calls.map(call=>call[1] as RequestInit)
    expect(requests).toHaveLength(3)
    expect(requests.map(request=>request.body)).toEqual([requests[0].body,requests[0].body,requests[0].body])
    expect(requests.map(request=>request.headers)).toEqual([requests[0].headers,requests[0].headers,requests[0].headers])
  })
  it('lets a definite validation response unlock editing and allocate a new key', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ error: 'validation_error' }), {
          status: 400,
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(receipt), { status: 201 })
      )
    vi.stubGlobal('fetch', fetcher)
    render(<ChatLeadForm />)
    const user = await fillForm()
    await user.click(
      screen.getByRole('button', { name: 'Registrar interesse' })
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('Revise')
    expect(screen.getByLabelText('Nome')).not.toHaveAttribute('readonly')
    await user.type(screen.getByLabelText('Nome'), ' Santos')
    await user.click(
      screen.getByRole('button', { name: 'Registrar interesse' })
    )
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Seu interesse foi registrado'
    )
    expect(fetcher.mock.calls[0][1].headers['Idempotency-Key']).not.toBe(
      fetcher.mock.calls[1][1].headers['Idempotency-Key']
    )
  })
})
