// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
beforeEach(() => {
  vi.resetModules()
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})
it('warms the read-only health route before issuing one official sign-in request', async () => {
  vi.useFakeTimers()
  let healthCalls = 0
  const posts: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/api/health')) {
        healthCalls += 1
        return healthCalls === 1
          ? new Response('<html>Starting</html>', {
              headers: { 'Content-Type': 'text/html' },
            })
          : json({ status: 'ok' })
      }
      if (init?.method === 'POST') posts.push(url)
      return json({ twoFactorRedirect: true, twoFactorMethods: ['totp'] })
    })
  )
  const { authAction, authClient } = await import('./auth-client')
  const result = authAction(
    () =>
      authClient.signIn.email({
        email: 'admin@example.com',
        password: 'a-strong-password',
      }),
    new AbortController().signal
  )
  expect(posts).toEqual([])
  await vi.advanceTimersByTimeAsync(1000)
  expect(await result).toMatchObject({ twoFactorRedirect: true })
  expect(posts).toHaveLength(1)
  expect(posts[0]).toBe(`${window.location.origin}/api/auth/sign-in/email`)
  expect(healthCalls).toBe(2)
})
it('does not replay an auth mutation after an uncertain network failure', async () => {
  let posts = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes('/api/health')) return json({ status: 'ok' })
      posts += 1
      throw new TypeError('network_lost')
    })
  )
  const { authAction, authClient } = await import('./auth-client')
  await expect(
    authAction(
      () =>
        authClient.signIn.email({
          email: 'admin@example.com',
          password: 'a-strong-password',
        }),
      new AbortController().signal
    )
  ).rejects.toThrow()
  expect(posts).toBe(1)
})
it.each([
  null,
  { session: { id: 's', expiresAt: 'invalid-date' }, user: { id: 'u' } },
  {
    session: { id: 's', expiresAt: '2000-01-01T00:00:00Z' },
    user: { id: 'u' },
  },
])(
  'treats a missing, malformed or expired server session as signed out',
  async (session) => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json(session))
    )
    const { getAuthSession } = await import('./auth-client')
    expect(await getAuthSession()).toBeNull()
  }
)
it('cancels startup without submitting credentials when the page leaves', async () => {
  vi.useFakeTimers()
  const controller = new AbortController()
  let posts = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes('/api/health'))
        return new Response('<html>Starting</html>', {
          headers: { 'Content-Type': 'text/html' },
        })
      posts += 1
      return json({})
    })
  )
  const { authAction, authClient } = await import('./auth-client')
  const result = authAction(
    () =>
      authClient.signIn.email({
        email: 'admin@example.com',
        password: 'a-strong-password',
      }),
    controller.signal
  )
  const rejection = expect(result).rejects.toThrow()
  controller.abort()
  await rejection
  expect(posts).toBe(0)
})

it('describes a rejected TOTP code as a code error even when the SDK returns HTTP 401', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) =>
      String(input).includes('/api/health')
        ? json({ status: 'ok' })
        : json({ code: 'INVALID_CODE', message: 'Invalid code' }, 401)
    )
  )
  const { authAction, authClient } = await import('./auth-client')
  await expect(
    authAction(
      () => authClient.twoFactor.verifyTotp({ code: '000000' }),
      new AbortController().signal
    )
  ).rejects.toThrow('Código inválido')
})

it('shows the server-provided remaining cooldown without replaying a blocked login', async () => {
  let posts = 0
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).includes('/api/health')) return json({ status: 'ok' })
    posts += 1
    return json({ message: 'Too many requests', retryAfterSeconds: 313 }, 429)
  }))
  const { authAction, authClient } = await import('./auth-client')
  await expect(authAction(() => authClient.signIn.email({ email: 'admin@example.com', password: 'a-strong-password' }), new AbortController().signal)).rejects.toThrow('Tente novamente em 6 minutos')
  expect(posts).toBe(1)
})
