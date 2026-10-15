import test from 'node:test'
import assert from 'node:assert/strict'
import { loadConfig } from '../server/config.ts'
test('refuses placing private SQLite in the public asset directory', () => {
  const previous = process.env.SQLITE_PATH
  try {
    process.env.SQLITE_PATH = 'public/assets/contacts.sqlite'
    assert.throws(() => loadConfig(), /SQLITE_PATH/)
    process.env.SQLITE_PATH = 'data/contacts.sqlite'
    assert.equal(loadConfig().databasePath, 'data/contacts.sqlite')
  } finally {
    if (previous === undefined) delete process.env.SQLITE_PATH
    else process.env.SQLITE_PATH = previous
  }
})
