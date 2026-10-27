import test from 'node:test'
import assert from 'node:assert/strict'
import { createDatabase } from '../server/db/database.ts'
import { asSqlDatabase, compilePostgres } from '../server/db/sql.ts'

test('Postgres binding preserves quoted SQL and binds positional/named parameters', () => {
  assert.deepEqual(compilePostgres("SELECT '?' literal, ? value", ['safe']), { sql: "SELECT '?' literal, $1 value", values: ['safe'] })
  assert.deepEqual(compilePostgres('SELECT @id, @id, @name', [{ id:'one', name:'two' }]), { sql:'SELECT $1, $2, $3', values:['one','one','two'] })
})
test('async SQLite adapter keeps concurrent requests outside transaction and rolls back all writes', async () => {
  const raw = createDatabase(':memory:')
  const db = asSqlDatabase(raw)
  try {
    await db.exec('CREATE TABLE adapter_test (id TEXT PRIMARY KEY)')
    let release
    let entered
    const ready = new Promise(r => { entered = r })
    const gate = new Promise(r => { release = r })
    const transaction = db.transaction(async () => {
      await db.prepare('INSERT INTO adapter_test VALUES (?)').run('inside')
      entered()
      await gate
      throw new Error('rollback')
    }).immediate()
    await ready
    const outside = db.prepare('INSERT INTO adapter_test VALUES (?)').run('outside')
    release()
    await assert.rejects(transaction, /rollback/)
    await outside
    assert.deepEqual(await db.prepare('SELECT id FROM adapter_test').all(), [{ id:'outside' }])
  } finally { raw.close() }
})
test('malformed PostgreSQL configuration never leaks credentials in inspected errors', async () => {
  const { createPostgresDatabase } = await import('../server/db/sql.ts')
  const { inspect } = await import('node:util')
  assert.throws(() => createPostgresDatabase('postgresql://user:dummy-test-only-secret@['), error => !inspect(error).includes('dummy-test-only-secret'))
})
