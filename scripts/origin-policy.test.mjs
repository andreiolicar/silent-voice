import test from 'node:test'
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { loadConfig } from '../server/config.ts'
import { createServer } from '../server/app.ts'
import { createDatabase } from '../server/db/database.ts'
import { provisionAdmin } from '../server/auth/password.ts'
import { cookie, validLead } from './helpers/api-fixture.mjs'

const ipOrigin = 'http://127.0.0.1:5173'
const nameOrigin = 'http://localhost:5173'
function configured(mode, origin) {
  const values = {
    NODE_ENV: mode,
    APP_ORIGIN: origin,
    SQLITE_PATH: ':memory:',
    DATABASE_URL: 'postgresql://fixture:fixture@localhost/fixture',
    SESSION_SECRET: 'test-origin-policy-secret-at-least-thirty-two-characters',
  }
  const previous = Object.fromEntries(
    Object.keys(values).map((key) => [key, process.env[key]])
  )
  try {
    Object.assign(process.env, values)
    return loadConfig()
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key]
      else process.env[key] = value
    }
  }
}
async function server(t, mode = 'development', origin = ipOrigin) {
  const database = createDatabase(':memory:')
  let calls = 0
  const app = await createServer({
    config: configured(mode, origin),
    database,
    chatProvider: {
      async *stream() {
        calls++
        yield { type: 'delta', text: 'Resposta de teste' }
        yield { type: 'done', finishReason: 'stop' }
      },
    },
  })
  t.after(async () => {
    await app.close()
    database.close()
  })
  return { app, database, calls: () => calls }
}
const chat = {
  requestId: 'origin-policy',
  messages: [{ id: 'visitor', role: 'user', content: 'Como funciona?' }],
}

for (const [configuredOrigin, visitorOrigin] of [
  [ipOrigin, nameOrigin],
  [ipOrigin, ipOrigin],
  [nameOrigin, ipOrigin],
]) {
  test(`development login/logout works from ${visitorOrigin} with configured ${configuredOrigin}`, async (t) => {
    const { app, database } = await server(t, 'development', configuredOrigin)
    await provisionAdmin(database, 'admin@example.com', 'a-long-test-password')
    const bootstrap = await app.inject('/api/auth/csrf')
    assert.equal(bootstrap.statusCode, 200)
    const initial = {
      origin: visitorOrigin,
      cookie: cookie(bootstrap),
      'x-csrf-token': bootstrap.json().csrfToken,
    }
    assert.equal(
      (
        await app.inject({
          method: 'POST',
          url: '/api/auth/login',
          headers: { origin: visitorOrigin, cookie: initial.cookie },
          payload: {
            email: 'admin@example.com',
            password: 'a-long-test-password',
          },
        })
      ).statusCode,
      403
    )
    const login = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      headers: initial,
      payload: { email: 'admin@example.com', password: 'a-long-test-password' },
    })
    assert.equal(login.statusCode, 200, login.body)
    const authenticated = {
      origin: visitorOrigin,
      cookie: cookie(login),
      'x-csrf-token': login.json().csrfToken,
    }
    assert.equal(
      (await app.inject({ url: '/api/auth/session', headers: authenticated }))
        .statusCode,
      200
    )
    assert.equal(
      (
        await app.inject({
          method: 'POST',
          url: '/api/auth/logout',
          headers: {
            ...authenticated,
            'x-csrf-token': initial['x-csrf-token'],
          },
        })
      ).statusCode,
      403
    )
    assert.equal(
      (
        await app.inject({
          method: 'POST',
          url: '/api/auth/logout',
          headers: authenticated,
        })
      ).statusCode,
      200
    )
    assert.equal(
      (await app.inject({ url: '/api/auth/session', headers: authenticated }))
        .statusCode,
      401
    )
  })
}
test('lead capture and chat share the development loopback policy', async (t) => {
  const { app, calls } = await server(t)
  for (const origin of [nameOrigin, ipOrigin]) {
    const lead = await app.inject({
      method: 'POST',
      url: '/api/leads',
      headers: { origin, 'idempotency-key': randomUUID() },
      payload: validLead,
    })
    assert.equal(lead.statusCode, 201)
    const response = await app.inject({
      method: 'POST',
      url: '/api/chat',
      headers: { origin },
      payload: chat,
    })
    assert.equal(response.statusCode, 200)
    assert.match(response.body, /"type":"done"/)
  }
  assert.equal(calls(), 2)
})
test('all mutation origin guards reject foreign, missing, changed-port/scheme and lookalike origins', async (t) => {
  const { app, calls } = await server(t)
  const bootstrap = await app.inject('/api/auth/csrf')
  let attempt = 0
  for (const origin of [
    undefined,
    'https://evil.example',
    'http://localhost:5174',
    'https://localhost:5173',
    'http://localhost.evil.example:5173',
    'http://127.0.0.2:5173',
    'http://localhost:5173/',
  ]) {
    for (const [url, payload] of [
      [
        '/api/auth/login',
        { email: 'admin@example.com', password: 'a-long-test-password' },
      ],
      ['/api/leads', validLead],
      ['/api/chat', chat],
    ]) {
      const headers = {
        cookie: cookie(bootstrap),
        'x-csrf-token': bootstrap.json().csrfToken,
        'idempotency-key': randomUUID(),
        ...(origin ? { origin } : {}),
      }
      const response = await app.inject({
        method: 'POST',
        url,
        remoteAddress: `192.0.2.${++attempt}`,
        headers,
        payload,
      })
      assert.equal(response.statusCode, 403, `${url}: ${origin}`)
    }
  }
  assert.equal(calls(), 0)
})
for (const [mode, origin, denied] of [
  ['production', ipOrigin, nameOrigin],
  ['production', nameOrigin, ipOrigin],
  ['development', 'https://silentvoice.example', nameOrigin],
]) {
  test(`${mode} ${origin} remains exact-only`, async (t) => {
    const { app, calls } = await server(t, mode, origin)
    for (const [url, payload] of [
      ['/api/leads', validLead],
      ['/api/chat', chat],
    ]) {
      assert.equal(
        (
          await app.inject({
            method: 'POST',
            url,
            headers: { origin: denied, 'idempotency-key': randomUUID() },
            payload,
          })
        ).statusCode,
        403
      )
      assert.equal(
        (
          await app.inject({
            method: 'POST',
            url,
            headers: { origin, 'idempotency-key': randomUUID() },
            payload,
          })
        ).statusCode,
        url === '/api/leads' ? 201 : 200
      )
    }
    assert.equal(calls(), 1)
  })
}
test('injected configs without an allowlist retain exact-origin behavior', async (t) => {
  const config = configured('development', ipOrigin)
  delete config.allowedOrigins
  const app = await createServer({
    config,
    chatProvider: {
      async *stream() {
        assert.fail('unapproved origin must not reach provider')
      },
    },
  })
  t.after(() => app.close())
  assert.equal(
    (
      await app.inject({
        method: 'POST',
        url: '/api/chat',
        headers: { origin: nameOrigin },
        payload: chat,
      })
    ).statusCode,
    403
  )
})
