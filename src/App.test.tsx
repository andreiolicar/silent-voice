import { render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { App } from './App'
afterEach(() => {
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})
it('direct admin entry renders authenticated route guard then login inside the actual app router', async () => {
  window.history.replaceState(null, '', '/admin')
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) =>
      String(input).includes('/auth/get-session')
        ? new Response('null', {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        : new Response(JSON.stringify({ csrfToken: 'test-token' }), {
            status: 200,
          })
    )
  )
  render(<App />)
  expect(
    await screen.findByLabelText('E-mail', { exact: true })
  ).toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: 'Abrir assistente Silent Voice' })
  ).not.toBeInTheDocument()
})
it('direct reset link bypasses the landing introduction and exposes the account form', async () => {
  window.history.replaceState(
    null,
    '',
    '/conta/redefinir-senha?token=reset-token&destino=app'
  )
  render(<App />)
  expect(
    await screen.findByLabelText('Nova senha', { exact: true })
  ).toBeInTheDocument()
  expect(
    screen.getByRole('link', { name: 'Continuar no aplicativo Silent Voice' })
  ).toHaveAttribute(
    'href',
    'silentvoicemobile://auth/reset-password?token=reset-token'
  )
  expect(
    screen.queryByRole('button', { name: 'Abrir assistente Silent Voice' })
  ).not.toBeInTheDocument()
})
