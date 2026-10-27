import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from '../server/app.ts'
const config = {
  port: 0,
  origin: 'http://127.0.0.1:5173',
  databasePath: ':memory:',
  sessionSecret: 'test-secret-thirty-two-characters-long',
  secureCookies: false,
  zaiModel: 'test',
  chatTimeoutMs: 5000,
  idleTimeoutMs: 4000,
}
const payload = {
  requestId: 'r',
  messages: [{ id: 'u', role: 'user', content: 'Olá' }],
}
const headers = { origin: config.origin }
test('two requests per IP and ten globally; completing requests frees exact slots', async () => {
  const gates = []
  const provider = {
    async *stream({ signal }) {
      await new Promise((resolve) => {
        gates.push(resolve)
        signal.addEventListener('abort', resolve, { once: true })
      })
      yield { type: 'done', finishReason: 'stop' }
    },
  }
  const app = await createServer({ config, chatProvider: provider })
  const pending = []
  try {
    for (let i = 0; i < 10; i++) {
      pending.push(
        app
          .inject({
            method: 'POST',
            url: '/api/chat',
            payload,
            headers,
            remoteAddress: `10.0.0.${Math.floor(i / 2) + 1}`,
          })
          .then((r) => r)
      )
      while (gates.length < i + 1)
        await new Promise((resolve) => setImmediate(resolve))
    }
    assert.equal(gates.length, 10)
    assert.equal(
      (
        await app.inject({
          method: 'POST',
          url: '/api/chat',
          payload,
          headers,
          remoteAddress: '10.0.0.1',
        })
      ).statusCode,
      429
    )
    assert.equal(
      (
        await app.inject({
          method: 'POST',
          url: '/api/chat',
          payload,
          headers,
          remoteAddress: '10.0.0.6',
        })
      ).statusCode,
      429
    )
    gates[0]()
    assert.equal((await pending[0]).statusCode, 200)
    const next = app.inject({
      method: 'POST',
      url: '/api/chat',
      payload,
      headers,
      remoteAddress: '10.0.0.1',
    })
    pending.push(next.then((r) => r))
    while (gates.length < 11)
      await new Promise((resolve) => setImmediate(resolve))
    assert.equal(gates.length, 11)
    for (const release of gates) release()
    await Promise.all(pending)
  } finally {
    for (const release of gates) release()
    await app.close()
  }
})
