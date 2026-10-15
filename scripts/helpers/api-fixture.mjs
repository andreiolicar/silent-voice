import { mkdtemp, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import assert from 'node:assert/strict'
import { createServer } from '../../server/app.ts'
import { createDatabase } from '../../server/db/database.ts'
import { provisionAdmin } from '../../server/auth/password.ts'

export const origin = 'http://127.0.0.1:5173'
export const validLead = {
  name: ' Maria Silva ',
  email: ' MARIA@EXAMPLE.COM ',
  objective: ' Gostaria de conhecer o dispositivo. ',
  profile: 'family',
  organization: ' Associação ',
}
export async function fixture(t) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'silent-voice-api-'))
  const databasePath = path.join(directory, 'test.sqlite')
  const config = {
    origin,
    databasePath,
    sessionSecret: 'test-session-secret-at-least-thirty-two-characters',
    secureCookies: false,
    port: 0,
    mistralModel: 'unused',
    chatTimeoutMs: 45000,
    idleTimeoutMs: 15000,
  }
  const database = createDatabase(databasePath)
  const chatProvider = {
    async *stream() {
      throw new Error('Data endpoints must never call the model')
    },
  }
  const app = await createServer({ config, database, chatProvider })
  t.after(async () => {
    await app.close()
    if (database.open) database.close()
    await rm(directory, { recursive: true, force: true })
  })
  return { app, database, directory, config, chatProvider }
}
export function cookie(response) {
  const value = response.headers['set-cookie']
  return (Array.isArray(value) ? value[0] : value)?.split(';')[0]
}
export async function login(app, database) {
  await provisionAdmin(database, 'admin@example.com', 'a-long-test-password')
  const csrf = await app.inject('/api/auth/csrf')
  assert.equal(csrf.statusCode, 200)
  const result = await app.inject({
    method: 'POST',
    url: '/api/auth/login',
    headers: {
      origin,
      cookie: cookie(csrf),
      'x-csrf-token': csrf.json().csrfToken,
    },
    payload: { email: 'ADMIN@example.com', password: 'a-long-test-password' },
  })
  assert.equal(result.statusCode, 200, result.body)
  assert.notEqual(result.json().csrfToken, csrf.json().csrfToken)
  assert.notEqual(
    cookie(result),
    cookie(csrf),
    'login rotates the actual pre-login session'
  )
  assert.match(result.headers['set-cookie'].toString(), /HttpOnly/)
  assert.match(result.headers['set-cookie'].toString(), /SameSite=Strict/i)
  return {
    cookie: cookie(result),
    origin,
    'x-csrf-token': result.json().csrfToken,
  }
}
