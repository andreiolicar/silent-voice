import test from 'node:test'
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import {
  fixture,
  origin,
  validLead,
  cookie,
  login,
} from './helpers/api-fixture.mjs'
import { createServer } from '../server/app.ts'
import { createDatabase } from '../server/db/database.ts'
import { hashPassword, verifyPassword } from '../server/auth/password.ts'

test('scrypt hashes use random salts and verify passwords without storing plaintext', async () => {
  const one = await hashPassword('a-long-test-password')
  const two = await hashPassword('a-long-test-password')
  assert.notEqual(one, two)
  assert.ok(!one.includes('a-long-test-password'))
  assert.equal(await verifyPassword('a-long-test-password', one), true)
  assert.equal(await verifyPassword('wrong', one), false)
  assert.equal(await verifyPassword('wrong', 'invalid'), false)
})
test('requires authenticated sessions and csrf, rotates login sessions, persists and invalidates logout', async (t) => {
  const { app, database, config, chatProvider } = await fixture(t)
  for (const url of [
    '/api/auth/session',
    '/api/admin/leads',
    '/api/admin/leads/no-id',
  ])
    assert.equal((await app.inject(url)).statusCode, 401)
  const anonymous = await app.inject('/api/auth/csrf')
  const headers = await login(app, database)
  assert.notEqual(cookie(anonymous), headers.cookie)
  assert.equal(
    (await app.inject({ url: '/api/auth/session', headers })).json().user.email,
    'admin@example.com'
  )
  const session = database
    .prepare('SELECT * FROM admin_sessions WHERE data LIKE ?')
    .get('%admin@example.com%')
  assert.ok(session)
  assert.ok(session.expires_at > Date.now())
  assert.ok(session.expires_at <= Date.now() + 8 * 60 * 60 * 1000)
  await app.inject({ url: '/api/auth/csrf', headers })
  await app.inject({ url: '/api/admin/leads', headers })
  assert.equal(
    database
      .prepare('SELECT expires_at FROM admin_sessions WHERE id = ?')
      .get(session.id).expires_at,
    session.expires_at,
    'reads do not extend absolute eight-hour lifetime'
  )
  assert.equal(
    (
      await app.inject({
        method: 'POST',
        url: '/api/auth/logout',
        headers: { cookie: headers.cookie, origin },
      })
    ).statusCode,
    403
  )
  assert.equal(
    (
      await app.inject({
        method: 'POST',
        url: '/api/auth/logout',
        headers: { ...headers, origin: 'https://evil.example' },
      })
    ).statusCode,
    403
  )
  await app.close()
  assert.ok(database.open, 'injected database remains open')
  database.close()
  const reopenedDatabase = createDatabase(config.databasePath)
  const restarted = await createServer({
    config,
    database: reopenedDatabase,
    chatProvider,
  })
  try {
    assert.equal(
      (await restarted.inject({ url: '/api/auth/session', headers }))
        .statusCode,
      200
    )
    assert.equal(
      (
        await restarted.inject({
          method: 'POST',
          url: '/api/auth/logout',
          headers,
        })
      ).statusCode,
      200
    )
    assert.equal(
      (await restarted.inject({ url: '/api/auth/session', headers }))
        .statusCode,
      401
    )
    assert.equal(
      reopenedDatabase
        .prepare('SELECT * FROM admin_sessions WHERE data LIKE ?')
        .get('%admin@example.com%'),
      undefined
    )
  } finally {
    await restarted.close()
    reopenedDatabase.close()
  }
})
test('enforces login origin and csrf, generic credentials errors and attempt limit', async (t) => {
  const { app } = await fixture(t)
  const csrf = await app.inject('/api/auth/csrf')
  const headers = {
    cookie: cookie(csrf),
    origin,
    'x-csrf-token': csrf.json().csrfToken,
  }
  const payload = { email: 'absent@example.com', password: 'wrong-password' }
  assert.equal(
    (
      await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        headers: { cookie: headers.cookie, origin },
        payload,
      })
    ).statusCode,
    403
  )
  assert.equal(
    (
      await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        headers: { ...headers, origin: 'https://evil.example' },
        payload,
      })
    ).statusCode,
    403
  )
  for (let i = 0; i < 5; i++) {
    const response = await app.inject({
      method: 'POST',
      url: '/api/auth/login',
      headers,
      payload,
    })
    if (response.statusCode === 429) break
    assert.equal(response.statusCode, 401)
    assert.ok(!response.body.includes(payload.email))
  }
  assert.equal(
    (
      await app.inject({
        method: 'POST',
        url: '/api/auth/login',
        headers,
        payload,
      })
    ).statusCode,
    429
  )
})
test('lists, filters, paginates and computes duplicate emails, notes and optimistic status conflicts', async (t) => {
  const { app, database } = await fixture(t)
  const headers = await login(app, database)
  const first = await app.inject({
    method: 'POST',
    url: '/api/leads',
    headers: { origin, 'idempotency-key': randomUUID() },
    payload: validLead,
  })
  const id = first.json().id
  await app.inject({
    method: 'POST',
    url: '/api/leads',
    headers: { origin, 'idempotency-key': randomUUID() },
    payload: { ...validLead, name: 'Outra pessoa' },
  })
  let listing = await app.inject({
    url: '/api/admin/leads?q=Silva&status=new&page=1',
    headers,
  })
  assert.equal(listing.statusCode, 200, listing.body)
  assert.equal(listing.json().total, 1)
  assert.equal(listing.json().items[0].duplicateEmail, true)
  assert.equal(listing.json().counts.new, 2)
  const initial = (
    await app.inject({ url: `/api/admin/leads/${id}`, headers })
  ).json()
  assert.deepEqual(initial.notes, [])
  assert.equal(initial.lead.version, 1)
  assert.equal(
    (
      await app.inject({
        method: 'PATCH',
        url: `/api/admin/leads/${id}`,
        headers: { origin, cookie: headers.cookie },
        payload: { status: 'contacted', version: 1 },
      })
    ).statusCode,
    403
  )
  const changed = await app.inject({
    method: 'PATCH',
    url: `/api/admin/leads/${id}`,
    headers,
    payload: { status: 'contacted', version: 1 },
  })
  assert.equal(changed.statusCode, 200, changed.body)
  assert.equal(changed.json().status, 'contacted')
  assert.equal(changed.json().version, 2)
  assert.equal(
    (
      await app.inject({
        method: 'PATCH',
        url: `/api/admin/leads/${id}`,
        headers,
        payload: { status: 'closed', version: 1 },
      })
    ).statusCode,
    409
  )
  const note = await app.inject({
    method: 'POST',
    url: `/api/admin/leads/${id}/notes`,
    headers,
    payload: { text: '  Primeiro contato realizado. ' },
  })
  assert.equal(note.statusCode, 201, note.body)
  assert.equal(note.json().author, 'admin@example.com')
  assert.equal(note.json().text, 'Primeiro contato realizado.')
  assert.equal(
    (await app.inject({ url: `/api/admin/leads/${id}`, headers })).json().notes
      .length,
    1
  )
  for (const query of [
    'page=0',
    'page=1.5',
    'status=bad',
    'from=2026-02-30',
    'from=tomorrow',
    'from=2026-10-02&to=2026-10-01',
    'unknown=value',
  ])
    assert.equal(
      (await app.inject({ url: `/api/admin/leads?${query}`, headers }))
        .statusCode,
      400,
      query
    )
  assert.equal(
    (
      await app.inject({
        method: 'POST',
        url: `/api/admin/leads/${id}/notes`,
        headers,
        payload: { text: 'x', author: 'spoof' },
      })
    ).statusCode,
    400
  )
  assert.equal(
    (
      await app.inject({
        method: 'PATCH',
        url: `/api/admin/leads/${id}`,
        headers,
        payload: { status: 'bad', version: 2 },
      })
    ).statusCode,
    400
  )
  assert.equal(
    (await app.inject({ url: `/api/admin/leads/${randomUUID()}`, headers }))
      .statusCode,
    404
  )
  listing = await app.inject({ url: '/api/admin/leads?status=closed', headers })
  assert.equal(listing.json().total, 0)
})
test('paginates twenty-five per page with stable date filters and rejects expired persisted sessions', async (t) => {
  const { app, database } = await fixture(t)
  const headers = await login(app, database)
  for (let index = 0; index < 27; index++) {
    const result = await app.inject({
      method: 'POST',
      url: '/api/leads',
      remoteAddress: `192.0.2.${index + 1}`,
      headers: { origin, 'idempotency-key': randomUUID() },
      payload: { ...validLead, name: `Contato ${index}` },
    })
    assert.equal(result.statusCode, 201)
  }
  const first = (await app.inject({ url: '/api/admin/leads', headers })).json()
  const second = (
    await app.inject({ url: '/api/admin/leads?page=2', headers })
  ).json()
  assert.equal(first.items.length, 25)
  assert.equal(second.items.length, 2)
  assert.equal(first.total, 27)
  assert.equal(first.items[0].name, 'Contato 26')
  assert.equal(
    new Set([...first.items, ...second.items].map((item) => item.id)).size,
    27
  )
  database
    .prepare('UPDATE leads SET created_at = ? WHERE id = ?')
    .run('2020-01-01T12:00:00.000Z', first.items[0].id)
  const historical = (
    await app.inject({
      url: '/api/admin/leads?from=2020-01-01&to=2020-01-01',
      headers,
    })
  ).json()
  assert.equal(historical.total, 1)
  assert.equal(historical.items[0].id, first.items[0].id)
  database.prepare('UPDATE admin_sessions SET expires_at = 0').run()
  assert.equal(
    (await app.inject({ url: '/api/admin/leads', headers })).statusCode,
    401
  )
  assert.equal(
    database.prepare('SELECT count(*) n FROM admin_sessions').get().n,
    0
  )
})
test('records the authenticated author for status changes', async (t) => {
  const { app, database } = await fixture(t)
  const headers = await login(app, database)
  const result = await app.inject({
    method: 'POST',
    url: '/api/leads',
    headers: { origin, 'idempotency-key': randomUUID() },
    payload: validLead,
  })
  const id = result.json().id
  const changed = await app.inject({
    method: 'PATCH',
    url: `/api/admin/leads/${id}`,
    headers,
    payload: { status: 'closed', version: 1 },
  })
  assert.equal(changed.statusCode, 200)
  const lead = database.prepare('SELECT * FROM leads WHERE id = ?').get(id)
  assert.equal(
    lead.status_updated_by,
    database.prepare('SELECT id FROM admin_users').get().id
  )
})

test('provisioning refuses password arguments and non-interactive password input', async () => {
  for (const args of [
    ['--email', 'admin@example.com', '--password', 'password-must-not-appear'],
    ['--email', 'admin@example.com'],
  ]) {
    const result = spawnSync(
      process.execPath,
      ['--experimental-strip-types', 'server/scripts/create-admin.ts', ...args],
      {
        cwd: process.cwd(),
        encoding: 'utf8',
        input: 'password-must-not-appear\n',
      }
    )
    assert.equal(result.status, 1)
    assert.ok(!result.stdout.includes('password-must-not-appear'))
    assert.ok(!result.stderr.includes('password-must-not-appear'))
  }
})
test('rejects internal notes longer than two thousand characters', async (t) => {
  const { app, database } = await fixture(t)
  const headers = await login(app, database)
  const lead = await app.inject({
    method: 'POST',
    url: '/api/leads',
    headers: { origin, 'idempotency-key': randomUUID() },
    payload: validLead,
  })
  const note = await app.inject({
    method: 'POST',
    url: `/api/admin/leads/${lead.json().id}/notes`,
    headers,
    payload: { text: 'x'.repeat(2001) },
  })
  assert.equal(note.statusCode, 400)
  assert.equal(database.prepare('SELECT count(*) n FROM lead_notes').get().n, 0)
})
