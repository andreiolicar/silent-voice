import test from 'node:test'
import assert from 'node:assert/strict'
import Database from 'better-sqlite3'
import { getMigrations } from 'better-auth/db/migration'
import { createAuth } from '../server/auth/better-auth.ts'
import { createServer } from '../server/app.ts'

const origin = 'http://127.0.0.1:5173'
async function fixture(t, trustProxy = false) {
  const database = new Database(':memory:')
  const config = { port: 0, origin, databasePath: ':memory:', sessionSecret: 'test-rate-limit-secret-at-least-32-characters', secureCookies: false, trustProxy, zaiModel: 'unused', chatTimeoutMs: 45000, idleTimeoutMs: 15000 }
  const auth = createAuth(config, database, async () => {})
  await (await getMigrations(auth.options)).runMigrations()
  const app = await createServer({ config, auth, chatProvider: { async *stream() { throw Error('unused') } } })
  t.after(async () => { await app.close(); database.close() })
  const attempt = (remoteAddress, headers = {}) => app.inject({ method: 'POST', url: '/api/auth/sign-in/email', remoteAddress, headers: { origin, ...headers }, payload: { email: 'invalid', password: 'invalid' } })
  return { app, database, attempt }
}

test('auth rate limits use the server-resolved client address, isolating clients and ignoring forged internal headers', async t => {
  const { attempt } = await fixture(t)
  for (let n = 0; n < 5; n++) assert.equal((await attempt('198.51.100.8')).statusCode, 400)
  assert.equal((await attempt('198.51.100.8', { 'x-forwarded-for': '203.0.113.9' })).statusCode, 429)
  assert.equal((await attempt('203.0.113.9', { 'x-forwarded-for': '198.51.100.8' })).statusCode, 400, 'one client must not consume another client’s login allowance')
})

test('trusted proxy chains cannot collapse clients into one bucket or use a spoofed leftmost address', async t => {
  const { attempt } = await fixture(t, true)
  for (let n = 0; n < 5; n++) assert.equal((await attempt('127.0.0.1', { 'x-forwarded-for': '192.0.2.1, 198.51.100.8' })).statusCode, 400)
  assert.equal((await attempt('127.0.0.1', { 'x-forwarded-for': '192.0.2.99, 198.51.100.8' })).statusCode, 429)
  assert.equal((await attempt('127.0.0.1', { 'x-forwarded-for': '192.0.2.1, 203.0.113.9' })).statusCode, 400)
})

test('rate rejection exposes the actual remaining cooldown without extending the blocked window', async t => {
  const { database, attempt } = await fixture(t)
  for (let n = 0; n < 5; n++) await attempt('198.51.100.8')
  const original = database.prepare('SELECT lastRequest FROM auth_rate_limit WHERE key LIKE ?').get('%|/sign-in/email').lastRequest
  const rejected = await attempt('198.51.100.8')
  assert.equal(rejected.statusCode, 429)
  assert.ok(Number(rejected.headers['retry-after']) > 0)
  assert.equal(rejected.json().retryAfterSeconds, Number(rejected.headers['retry-after']))
  assert.equal(database.prepare('SELECT lastRequest FROM auth_rate_limit WHERE key LIKE ?').get('%|/sign-in/email').lastRequest, original)
  database.prepare('UPDATE auth_rate_limit SET lastRequest = ? WHERE key LIKE ?').run(Date.now() - 901000, '%|/sign-in/email')
  assert.equal((await attempt('198.51.100.8')).statusCode, 400, 'the same client can try again after the actual window expires')
})
