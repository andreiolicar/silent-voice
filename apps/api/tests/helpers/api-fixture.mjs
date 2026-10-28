import { mkdtemp, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import assert from 'node:assert/strict'
import { createServer } from '../../src/app.ts'
import { createDatabase } from '../../src/db/database.ts'
import {testAuth,signInAdmin} from './test-auth.mjs'

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
    zaiModel: 'unused',
    chatTimeoutMs: 45000,
    idleTimeoutMs: 15000,
  }
  const database = createDatabase(databasePath)
  const chatProvider = {
    async *stream() {
      throw new Error('Data endpoints must never call the model')
    },
  }
  const auth=await testAuth(database,config)
  const app = await createServer({ config, database, chatProvider,auth })
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
  return signInAdmin(app,database)
}
