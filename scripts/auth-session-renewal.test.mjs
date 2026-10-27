import test from 'node:test'
import assert from 'node:assert/strict'
import { fixture, login } from './helpers/api-fixture.mjs'
import { requireAdmin } from '../server/auth/routes.ts'

const day = 86400_000
async function guardedSession(t) {
  const { app, database } = await fixture(t)
  app.addHook('onRequest', async (request, reply) => {
    if (request.url === '/protected')
      reply.header('Set-Cookie', 'app_context=kept; Path=/; HttpOnly')
  })
  app.get('/protected', { preHandler: requireAdmin }, async () => ({
    ok: true,
  }))
  const headers = await login(app, database)
  const authenticated = await app.inject({
    url: '/api/auth/get-session',
    headers,
  })
  assert.equal(authenticated.statusCode, 200, authenticated.body)
  const session = authenticated.json()
  const { internalAdapter } = await app.auth.$context
  return { app, headers, session, internalAdapter }
}
function setCookies(response) {
  const value = response.headers['set-cookie']
  return value ? (Array.isArray(value) ? value : [value]) : []
}
for (const [role, mfa, status, code] of [
  ['admin', true, 200, undefined],
  ['user', true, 403, 'FORBIDDEN'],
  ['admin', false, 403, 'MFA_SETUP_REQUIRED'],
]) {
  test(`CRM guard forwards every SDK renewal/cleanup cookie on ${status} ${code || 'authorized'}`, async (t) => {
    const { app, headers, session, internalAdapter } = await guardedSession(t)
    const oldExpiry = new Date(Date.now() + 5 * day)
    await internalAdapter.updateSession(session.session.token, {
      expiresAt: oldExpiry,
      updatedAt: new Date(Date.now() - 2 * day),
    })
    await internalAdapter.updateUser(session.user.id, {
      role,
      twoFactorEnabled: mfa,
    })
    // Stale SDK cache data yields an additional cleanup cookie even though cookie caching is disabled.
    const response = await app.inject({
      url: '/protected',
      headers: {
        ...headers,
        cookie: headers.cookie + '; better-auth.session_data=stale',
      },
    })
    assert.equal(response.statusCode, status, response.body)
    if (code) assert.equal(response.json().code, code)
    const cookies = setCookies(response)
    assert.ok(
      cookies.some((value) => value.startsWith('app_context=kept;')),
      'preexisting response cookie is preserved'
    )
    assert.ok(
      cookies.some(
        (value) =>
          value.startsWith('better-auth.session_token=') &&
          /Max-Age=604800/i.test(value)
      ),
      'browser cookie receives the full renewed session lifetime'
    )
    assert.ok(
      cookies.some(
        (value) =>
          value.startsWith('better-auth.session_data=;') &&
          /Max-Age=0/i.test(value)
      ),
      'SDK cache cleanup cookie is also forwarded'
    )
    const stored = await internalAdapter.findSession(session.session.token)
    assert.ok(
      stored.session.expiresAt > oldExpiry,
      'the SDK refreshed the persistent session'
    )
    const following = await app.inject({
      url: '/api/auth/get-session',
      headers,
    })
    assert.equal(following.statusCode, 200, following.body)
    assert.ok(
      !setCookies(following).some((value) =>
        value.startsWith('better-auth.session_token=')
      ),
      'a following session request cannot repair an already-consumed daily renewal'
    )
  })
}
test('CRM guard forwards SDK cookie removal when the authoritative session has expired', async (t) => {
  const { app, headers, session, internalAdapter } = await guardedSession(t)
  await internalAdapter.updateSession(session.session.token, {
    expiresAt: new Date(Date.now() - day),
    updatedAt: new Date(Date.now() - 8 * day),
  })
  const response = await app.inject({ url: '/protected', headers })
  assert.equal(response.statusCode, 401, response.body)
  const cookies = setCookies(response)
  assert.ok(
    cookies.some((value) => value.startsWith('app_context=kept;')),
    'preexisting cookie is preserved on denial'
  )
  assert.ok(
    cookies.some(
      (value) =>
        value.startsWith('better-auth.session_token=;') &&
        /Max-Age=0/i.test(value)
    ),
    'expired browser session cookie is cleared'
  )
  assert.equal(await internalAdapter.findSession(session.session.token), null)
})
