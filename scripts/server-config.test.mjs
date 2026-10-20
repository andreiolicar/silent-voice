import test from 'node:test'
import assert from 'node:assert/strict'
import { loadConfig } from '../server/config.ts'
test('selects GLM without reusing legacy provider credentials and allows an explicit model override', () => {
  const names = ['ZAI_API_KEY', 'ZAI_MODEL', 'GEMINI_API_KEY', 'GEMINI_MODEL', 'MISTRAL_API_KEY', 'MISTRAL_MODEL']
  const previous = Object.fromEntries(names.map(name => [name, process.env[name]]))
  try {
    delete process.env.ZAI_API_KEY
    delete process.env.ZAI_MODEL
    process.env.MISTRAL_API_KEY = 'legacy-fixture-key'
    process.env.MISTRAL_MODEL = 'legacy-model'
    process.env.GEMINI_API_KEY = 'legacy-google-key'
    process.env.GEMINI_MODEL = 'legacy-google-model'
    assert.equal(loadConfig().zaiApiKey, undefined)
    assert.equal(loadConfig().zaiModel, 'glm-4.5-flash')
    process.env.ZAI_API_KEY = 'zai-fixture-key'
    process.env.ZAI_MODEL = 'glm-explicit-test-model'
    assert.equal(loadConfig().zaiApiKey, 'zai-fixture-key')
    assert.equal(loadConfig().zaiModel, 'glm-explicit-test-model')
  } finally {
    for (const name of names) {
      if (previous[name] === undefined) delete process.env[name]
      else process.env[name] = previous[name]
    }
  }
})
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
