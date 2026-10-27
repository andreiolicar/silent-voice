import test from 'node:test'
import assert from 'node:assert/strict'
import { consumeChatStream } from '../src/features/chatbot/sse-parser.ts'
function response(text, size = 3) {
  const data = new TextEncoder().encode(text)
  return new Response(
    new ReadableStream({
      start(c) {
        for (let i = 0; i < data.length; i += size)
          c.enqueue(data.slice(i, i + size))
        c.close()
      },
    }),
    { headers: { 'Content-Type': 'text/event-stream' } }
  )
}
const frame = (e) => `data: ${JSON.stringify(e)}\r\n\r\n`
test('SSE preserves fragmented UTF8, CRLF and request IDs through confirmed done', async () => {
  const events = []
  await consumeChatStream(
    response(
      frame({ type: 'delta', requestId: 'r', text: 'Olá 👋' }) +
        frame({ type: 'done', requestId: 'r', finishReason: 'stop' }),
      1
    ),
    new AbortController().signal,
    (e) => events.push(e)
  )
  assert.equal(events[0].text, 'Olá 👋')
  assert.equal(events.at(-1).type, 'done')
})
test('SSE rejects truncated, malformed or spoofed event types rather than inventing success', async () => {
  for (const text of [
    frame({ type: 'delta', requestId: 'r', text: 'partial' }),
    'data: <script>\n\n',
    frame({ type: 'open-url', url: 'javascript:alert(1)' }),
  ])
    await assert.rejects(
      consumeChatStream(response(text), new AbortController().signal, () => {})
    )
})
test('server error is delivered and does not require fake done', async () => {
  const events = []
  await consumeChatStream(
    response(
      frame({ type: 'error', requestId: 'r', code: 'timeout', retryable: true })
    ),
    new AbortController().signal,
    (e) => events.push(e)
  )
  assert.equal(events[0].code, 'timeout')
})
test('cancel releases reader even when stream never finishes', async () => {
  let cancelled = false
  const controller = new AbortController()
  const res = new Response(
    new ReadableStream({
      cancel() {
        cancelled = true
      },
    })
  )
  const promise = consumeChatStream(res, controller.signal, () => {})
  controller.abort()
  await assert.rejects(promise)
  assert.equal(cancelled, true)
})
