import test from 'node:test'
import assert from 'node:assert/strict'
import { fixture, origin } from './helpers/api-fixture.mjs'
const submit = (app, payload, headers = {}, remoteAddress = '127.0.0.1') =>
  app.inject({
    method: 'POST',
    url: '/api/waitlist',
    headers: { origin, ...headers },
    payload,
    remoteAddress,
  })

test('waitlist persists normalized emails and concurrent retries create a single entry without exposing membership', async (t) => {
  const { app, database } = await fixture(t)
  const responses = await Promise.all([
    submit(app, { email: ' TEST@EXAMPLE.COM ' }),
    submit(app, { email: 'test@example.com' }),
    submit(app, { email: 'test@example.com' }),
  ])
  for (const result of responses) {
    assert.equal(result.statusCode, 200, result.body)
    assert.deepEqual(result.json(), { registered: true })
  }
  const rows = database.prepare('SELECT * FROM waitlist_entries').all()
  assert.equal(rows.length, 1)
  assert.equal(rows[0].email, 'test@example.com')
  assert.ok(Number.isFinite(Date.parse(rows[0].created_at)))
  assert.equal(database.prepare('SELECT count(*) n FROM leads').get().n, 0)
})

test('waitlist rejects invalid input and cross-origin requests without storing emails', async (t) => {
  const { app, database } = await fixture(t)
  for (const payload of [
    { email: 'bad' },
    { email: 'a@b.com', name: 'extra' },
    {},
    { email: 'a'.repeat(255) + '@example.com' },
  ])
    assert.equal((await submit(app, payload)).statusCode, 400)
  assert.equal(
    (
      await submit(
        app,
        { email: 'test@example.com' },
        { origin: 'https://evil.example' },
        '127.0.0.2',
      )
    ).statusCode,
    403,
  )
  assert.equal(
    (
      await app.inject({
        method: 'POST',
        url: '/api/waitlist',
        payload: { email: 'test@example.com' },
        remoteAddress: '127.0.0.3',
      })
    ).statusCode,
    403,
  )
  assert.equal(
    database.prepare('SELECT count(*) n FROM waitlist_entries').get().n,
    0,
  )
})

test('waitlist rate limits submissions', async (t) => {
  const { app } = await fixture(t)
  for (let i = 0; i < 5; i++)
    assert.equal(
      (await submit(app, { email: 'test@example.com' })).statusCode,
      200,
    )
  assert.equal(
    (await submit(app, { email: 'test@example.com' })).statusCode,
    429,
  )
})
