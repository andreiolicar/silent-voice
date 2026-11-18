import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Waitlist } from './Waitlist'
afterEach(() => vi.unstubAllGlobals())
function http(submit: () => Promise<Response>) {
  vi.stubGlobal('fetch', (url: string) =>
    url === '/api/health'
      ? Promise.resolve(Response.json({ status: 'ok' }))
      : submit(),
  )
}
function fill() {
  fireEvent.change(screen.getByLabelText('Seu e-mail'), {
    target: { value: 'person@example.com' },
  })
}
it('rejects invalid input without transmitting it', () => {
  const submit = vi.fn()
  http(submit)
  render(<Waitlist />)
  fireEvent.click(screen.getByRole('button', { name: 'Entrar na lista' }))
  expect(screen.getByLabelText('Seu e-mail')).toHaveAttribute(
    'aria-invalid',
    'true',
  )
  expect(submit).not.toHaveBeenCalled()
})
it('does not confirm a malformed receipt and allows retry with the same address', async () => {
  const submit = vi
    .fn()
    .mockResolvedValueOnce(Response.json({}))
    .mockResolvedValueOnce(Response.json({ registered: true }))
  http(submit)
  render(<Waitlist />)
  fill()
  fireEvent.click(screen.getByRole('button', { name: 'Entrar na lista' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Não foi possível confirmar',
  )
  expect(screen.queryByText('Você está na lista.')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  expect(await screen.findByText('Você está na lista.')).toBeVisible()
  expect(submit).toHaveBeenCalledTimes(2)
})
it('locks repeated submissions until the server responds', async () => {
  let resolve!: (r: Response) => void
  const submit = vi.fn(
    () =>
      new Promise<Response>((r) => {
        resolve = r
      }),
  )
  http(submit)
  render(<Waitlist />)
  fill()
  const button = screen.getByRole('button', { name: 'Entrar na lista' })
  fireEvent.click(button)
  fireEvent.click(button)
  await waitFor(() => expect(submit).toHaveBeenCalledTimes(1))
  expect(button).toBeDisabled()
  resolve(Response.json({ registered: true }))
  expect(await screen.findByText('Você está na lista.')).toBeVisible()
})
it('handles unavailable submission without clearing the email', async () => {
  http(async () => {
    throw new Error('offline')
  })
  render(<Waitlist />)
  fill()
  fireEvent.click(screen.getByRole('button', { name: 'Entrar na lista' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Não foi possível confirmar',
  )
  expect(screen.getByLabelText('Seu e-mail')).toHaveValue('person@example.com')
})

it('rejects addresses disallowed by the API before sending', async () => {
  const submit = vi
    .fn()
    .mockResolvedValue(Response.json({ error: 'invalid' }, { status: 400 }))
  http(submit)
  render(<Waitlist />)
  fireEvent.change(screen.getByLabelText('Seu e-mail'), {
    target: { value: 'ana..silva@example.com' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Entrar na lista' }))
  expect(screen.getByLabelText('Seu e-mail')).toHaveAttribute(
    'aria-invalid',
    'true',
  )
  expect(screen.getByRole('alert')).toHaveTextContent(
    'Informe um e-mail válido.',
  )
  expect(submit).not.toHaveBeenCalled()
})

it('associates a server validation rejection with the email field', async () => {
  http(async () => Response.json({ error: 'invalid' }, { status: 400 }))
  render(<Waitlist />)
  fill()
  fireEvent.click(screen.getByRole('button', { name: 'Entrar na lista' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Informe um e-mail válido.',
  )
  expect(screen.getByLabelText('Seu e-mail')).toHaveAttribute(
    'aria-invalid',
    'true',
  )
})
