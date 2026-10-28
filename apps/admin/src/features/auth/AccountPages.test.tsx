// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router-dom'
import { AccountPages } from './AccountPages'
const sdk = vi.hoisted(() => ({ resetPassword: vi.fn() }))
vi.mock('better-auth/react', () => ({ createAuthClient: () => sdk }))
function mount(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <AccountPages />
    </MemoryRouter>
  )
}
beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(JSON.stringify({ status: 'ok' }), {
          headers: { 'Content-Type': 'application/json' },
        })
    )
  )
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
it('uses only the fixed app reset destination and URL-encodes the reset token', () => {
  mount(
    '/conta/redefinir-senha?token=abc%26next%3Devil&destino=app&redirect=https://evil.example'
  )
  expect(
    screen.getByRole('link', { name: 'Continuar no aplicativo Silent Voice' })
  ).toHaveAttribute(
    'href',
    'silentvoicemobile://auth/reset-password?token=abc%26next%3Devil'
  )
})
it('uses the fixed confirmation handoff without forwarding arbitrary destinations', () => {
  mount('/conta/email-confirmado?destino=app&redirect=somethingelse://account')
  expect(
    screen.getByRole('link', { name: 'Continuar no aplicativo Silent Voice' })
  ).toHaveAttribute('href', 'silentvoicemobile://auth/email-confirmed')
})
it.each([
  '/conta/redefinir-senha',
  '/conta/redefinir-senha?token=old&error=INVALID_TOKEN',
  '/conta/email-confirmado?error=invalid',
])('does not offer reset or an app handoff for an invalid link: %s', (path) => {
  mount(path)
  expect(screen.getByRole('alert')).toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: 'Salvar nova senha' })
  ).not.toBeInTheDocument()
  expect(
    screen.queryByRole('link', { name: 'Continuar no aplicativo Silent Voice' })
  ).not.toBeInTheDocument()
})
it('requires matching passwords and shows the server-confirmed reset success', async () => {
  sdk.resetPassword.mockResolvedValue({ data: { status: true }, error: null })
  mount('/conta/redefinir-senha?token=reset-token')
  fireEvent.change(screen.getByLabelText('Nova senha'), {
    target: { value: 'new-strong-password' },
  })
  fireEvent.change(screen.getByLabelText('Confirmar nova senha'), {
    target: { value: 'different-password' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Salvar nova senha' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'As senhas precisam ser iguais'
  )
  expect(sdk.resetPassword).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Confirmar nova senha'), {
    target: { value: 'new-strong-password' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Salvar nova senha' }))
  expect(
    await screen.findByRole('heading', { name: 'Senha redefinida' })
  ).toBeInTheDocument()
  expect(screen.queryByLabelText('Nova senha')).not.toBeInTheDocument()
  expect(sdk.resetPassword).toHaveBeenCalledWith(
    expect.objectContaining({
      token: 'reset-token',
      newPassword: 'new-strong-password',
    })
  )
})
it('shows an expired token error without claiming a password reset or replaying it', async () => {
  sdk.resetPassword.mockResolvedValue({
    data: null,
    error: { code: 'INVALID_TOKEN', status: 400 },
  })
  mount('/conta/redefinir-senha?token=used-token')
  fireEvent.change(screen.getByLabelText('Nova senha'), {
    target: { value: 'new-strong-password' },
  })
  fireEvent.change(screen.getByLabelText('Confirmar nova senha'), {
    target: { value: 'new-strong-password' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Salvar nova senha' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Este link expirou ou já foi utilizado'
  )
  expect(
    screen.queryByRole('heading', { name: 'Senha redefinida' })
  ).not.toBeInTheDocument()
  expect(sdk.resetPassword).toHaveBeenCalledTimes(1)
  expect(screen.getByLabelText('Nova senha')).toHaveValue('')
})
