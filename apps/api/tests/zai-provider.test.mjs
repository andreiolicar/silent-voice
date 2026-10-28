import test from 'node:test'
import assert from 'node:assert/strict'
import { ZaiProvider } from '../src/chat/zai-provider.ts'

const options = { apiKey: 'private-fixture-key', model: 'glm-4.5-flash', uiPrompt: 'UI instructions' }
const messages = [{ role: 'system', content: 'product facts' }, { role: 'user', content: 'question' }]
const collect = async (provider, signal = new AbortController().signal) => {
  const events = []
  for await (const event of provider.stream({ messages, signal })) events.push(event)
  return events
}
const frame = (value) => `data: ${JSON.stringify(value)}\r\n\r\n`
function response(text, onCancel = () => {}) {
  const bytes = new TextEncoder().encode(text)
  return new Response(new ReadableStream({
    start(controller) {
      for (let offset = 0; offset < bytes.length; offset += 7)
        controller.enqueue(bytes.slice(offset, offset + 7))
      controller.close()
    },
    cancel: onCancel,
  }), { headers: { 'Content-Type': 'text/event-stream' } })
}

test('Z.ai streams fragmented UTF8, excludes reasoning and preserves the controlled request', async () => {
  const controller = new AbortController()
  let observed
  const provider = new ZaiProvider(options, async (url, init) => {
    observed = { url, ...init, body: JSON.parse(init.body) }
    return response(': heartbeat\r\n\r\n' + frame({ choices: [{ delta: { reasoning_content: 'private', content: 'Olá 👋' } }] }) +
      frame({ choices: [{ delta: {}, finish_reason: 'stop' }] }) + 'data: [DONE]\r\n\r\n')
  })
  assert.deepEqual(await collect(provider, controller.signal), [
    { type: 'delta', text: 'Olá 👋' }, { type: 'done', finishReason: 'stop' },
  ])
  assert.equal(observed.url, 'https://api.z.ai/api/paas/v4/chat/completions')
  assert.equal(observed.signal, controller.signal)
  assert.equal(observed.headers.Authorization, 'Bearer private-fixture-key')
  assert.equal(observed.body.model, 'glm-4.5-flash')
  assert.equal(observed.body.stream, true)
  assert.deepEqual(observed.body.thinking, { type: 'disabled' })
  assert.equal(observed.body.max_tokens, 2048)
  assert.match(observed.body.messages[0].content, /product facts/)
  assert.match(observed.body.messages[0].content, /UI instructions/)
  assert.deepEqual(observed.body.messages[1], messages[1])
  assert.equal(observed.body.tools, undefined)
})

test('Z.ai preserves exhaustion and blocked finishes instead of inventing success', async () => {
  for (const [reason, expected] of [['length', 'length'], ['sensitive', 'other'], ['tool_calls', 'other']]) {
    const provider = new ZaiProvider(options, async () => response(frame({ choices: [{ delta: {}, finish_reason: reason }] })))
    assert.deepEqual(await collect(provider), [{ type: 'done', finishReason: expected }])
  }
})

test('Z.ai propagates HTTP status without exposing the upstream body or retrying', async () => {
  let calls = 0
  const provider = new ZaiProvider(options, async () => {
    calls++
    return new Response('private-fixture-key sensitive upstream details', { status: 429 })
  })
  await assert.rejects(() => collect(provider), error => error.status === 429 && !error.message.includes('private-fixture'))
  assert.equal(calls, 1)
})

test('Z.ai missing credentials never calls the provider', async () => {
  const provider = new ZaiProvider({ model: 'glm-4.5-flash', uiPrompt: '' }, async () => assert.fail('no request'))
  await assert.rejects(() => collect(provider), /not configured/)
})

test('Z.ai EOF or DONE without a finish reason cannot become a completed answer', async () => {
  for (const ending of ['', 'data: [DONE]\r\n\r\n']) {
    const provider = new ZaiProvider(options, async () => response(frame({ choices: [{ delta: { content: 'partial' } }] }) + ending))
    assert.deepEqual(await collect(provider), [{ type: 'delta', text: 'partial' }])
  }
})

test('Z.ai rejects malformed, upstream-error and oversized frames', async () => {
  for (const content of ['data: {broken}\n\n', frame({ error: { message: 'private error' } }), 'data: ' + 'x'.repeat(70001)]) {
    const provider = new ZaiProvider(options, async () => response(content))
    await assert.rejects(() => collect(provider))
  }
})

test('Z.ai cancellation aborts a pending stream and releases its reader', async () => {
  const abort = new AbortController()
  let cancelled = false
  const provider = new ZaiProvider(options, async () => new Response(new ReadableStream({ cancel() { cancelled = true } })))
  const result = collect(provider, abort.signal)
  await new Promise(resolve => setImmediate(resolve))
  abort.abort()
  await assert.rejects(() => result, { name: 'AbortError' })
  assert.equal(cancelled, true)
})

test('Z.ai consumer cancellation closes upstream even without an HTTP abort', async () => {
  let cancelled = false
  const provider = new ZaiProvider(options, async () => new Response(new ReadableStream({
    start(controller) { controller.enqueue(new TextEncoder().encode(frame({ choices: [{ delta: { content: 'partial' } }] }))) },
    cancel() { cancelled = true },
  })))
  for await (const event of provider.stream({ messages, signal: new AbortController().signal })) {
    assert.equal(event.text, 'partial')
    break
  }
  assert.equal(cancelled, true)
})
