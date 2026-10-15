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
      String(input).endsWith('/auth/session')
        ? new Response(JSON.stringify({ error: 'auth' }), { status: 401 })
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
