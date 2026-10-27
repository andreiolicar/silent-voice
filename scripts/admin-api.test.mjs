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
        headers: { origin: 'https://evil.example', cookie: headers.cookie },
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
  database.prepare('UPDATE auth_session SET expiresAt = 0').run()
  assert.equal(
    (await app.inject({ url: '/api/admin/leads', headers })).statusCode,
    401
  )
  assert.equal(
    database.prepare('SELECT count(*) n FROM auth_session').get().n,
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
