import test from 'node:test'
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { fixture, origin, validLead } from './helpers/api-fixture.mjs'
import { createServer } from '../server/app.ts'
import { createDatabase } from '../server/db/database.ts'
import { backupDatabase } from '../server/db/backup.ts'
import path from 'node:path'
import { spawnSync } from 'node:child_process'

function submit(
  app,
  payload = validLead,
  key = randomUUID(),
  headers = {},
  remoteAddress
) {
  return app.inject({
    method: 'POST',
    url: '/api/leads',
    remoteAddress,
    headers: { origin, 'idempotency-key': key, ...headers },
    payload,
  })
}
test('commits normalized leads and replays the original receipt across database reopen', async (t) => {
  const { app, database, directory, config, chatProvider } = await fixture(t)
  const key = randomUUID()
  const created = await submit(app, validLead, key)
  assert.equal(created.statusCode, 201, created.body)
  assert.match(created.json().id, /^[0-9a-f-]{36}$/)
  assert.ok(Number.isFinite(Date.parse(created.json().createdAt)))
  const replay = await submit(
    app,
    {
      ...validLead,
      name: 'Maria Silva',
      email: 'maria@example.com',
      objective: validLead.objective.trim(),
      organization: 'Associação',
    },
    key
  )
  assert.equal(replay.statusCode, 200)
  assert.deepEqual(replay.json(), created.json())
  assert.equal(
    (await submit(app, { ...validLead, name: 'Outro nome' }, key)).statusCode,
    422
  )
  assert.equal(
    (await submit(app)).statusCode,
    201,
    'same email can create a legitimate new request'
  )
  const stored = database.prepare('SELECT * FROM leads ORDER BY rowid').all()
  assert.equal(stored.length, 2)
  assert.equal(stored[0].email, 'maria@example.com')
  assert.equal(stored[0].name, 'Maria Silva')
  const backup = path.join(directory, 'restored.sqlite')
  await backupDatabase(database, backup)
  const restored = createDatabase(backup)
  try {
    assert.equal(restored.prepare('SELECT count(*) n FROM leads').get().n, 2)
    assert.equal(
      restored.prepare('SELECT count(*) n FROM lead_submissions').get().n,
      2
    )
    assert.deepEqual(restored.pragma('foreign_key_check'), [])
    const reopened = await createServer({
      config,
      database: restored,
      chatProvider,
    })
    try {
      const retryAfterRestore = await submit(reopened, validLead, key)
      assert.equal(retryAfterRestore.statusCode, 200)
      assert.deepEqual(retryAfterRestore.json(), created.json())
    } finally {
      await reopened.close()
    }
  } finally {
    restored.close()
  }
})
test('rejects malformed input, unknown fields and missing origin without leaking input', async (t) => {
  const { app, database } = await fixture(t)
  for (const change of [
    { name: 'A' },
    { email: 'invalid' },
    { objective: 'short' },
    { profile: 'unknown' },
    { organization: 'x'.repeat(151) },
    { unexpected: 'secret-value' },
  ]) {
    const result = await submit(
      app,
      { ...validLead, ...change },
      randomUUID(),
      {},
      randomUUID()
    )
    assert.equal(result.statusCode, 400, result.body)
    assert.ok(!result.body.includes('secret-value'))
  }
  assert.equal((await submit(app, validLead, 'invalid')).statusCode, 400)
  assert.equal(
    (
      await submit(app, validLead, randomUUID(), {
        origin: 'https://evil.example',
      })
    ).statusCode,
    403
  )
  assert.equal(
    (
      await app.inject({
        method: 'POST',
        url: '/api/leads',
        headers: { 'idempotency-key': randomUUID() },
        payload: validLead,
      })
    ).statusCode,
    403
  )
  assert.equal(database.prepare('SELECT count(*) n FROM leads').get().n, 0)
})
test('limits public lead submissions to five per fifteen minutes', async (t) => {
  const { app } = await fixture(t)
  for (let i = 0; i < 5; i++) assert.equal((await submit(app)).statusCode, 201)
  assert.equal((await submit(app)).statusCode, 429)
})
test('simultaneous retries produce one durable lead and a failed receipt insert rolls back its lead', async (t) => {
  const { app, database } = await fixture(t)
  const key = randomUUID()
  const results = await Promise.all([
    submit(app, validLead, key),
    submit(app, validLead, key),
  ])
  assert.deepEqual(results.map((item) => item.statusCode).sort(), [200, 201])
  assert.deepEqual(results[0].json(), results[1].json())
  assert.equal(database.prepare('SELECT count(*) n FROM leads').get().n, 1)
  database.exec(
    "CREATE TRIGGER reject_submission BEFORE INSERT ON lead_submissions BEGIN SELECT RAISE(ABORT, 'forced test failure'); END"
  )
  const failed = await submit(app)
  assert.equal(failed.statusCode, 500)
  assert.ok(!failed.body.includes('forced test failure'))
  assert.ok(!failed.body.includes('MARIA'))
  assert.equal(database.prepare('SELECT count(*) n FROM leads').get().n, 1)
})

test('database opens with all six tables and enforced constraints; backup CLI creates a usable snapshot', async (t) => {
  const { app, database, directory, config } = await fixture(t)
  assert.equal(database.pragma('journal_mode', { simple: true }), 'wal')
  assert.equal(database.pragma('foreign_keys', { simple: true }), 1)
  assert.equal(database.pragma('busy_timeout', { simple: true }), 5000)
  assert.deepEqual(
    database
      .prepare(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
      )
      .all()
      .map((item) => item.name),
    [
      'admin_sessions',
      'admin_users',
      'lead_notes',
      'lead_submissions',
      'leads',
      'schema_migrations',
    ]
  )
  assert.equal((await submit(app)).statusCode, 201)
  const destination = path.join(directory, 'cli-backup.sqlite')
  const backup = spawnSync(
    process.execPath,
    ['--experimental-strip-types', 'server/scripts/backup.ts', destination],
    {
      cwd: process.cwd(),
      env: { ...process.env, SQLITE_PATH: config.databasePath },
      encoding: 'utf8',
    }
  )
  assert.equal(backup.status, 0, backup.stderr)
  const restored = createDatabase(destination)
  try {
    assert.equal(restored.prepare('SELECT count(*) n FROM leads').get().n, 1)
    assert.equal(restored.pragma('integrity_check', { simple: true }), 'ok')
    assert.deepEqual(restored.pragma('foreign_key_check'), [])
  } finally {
    restored.close()
  }
})
