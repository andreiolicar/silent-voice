import test from 'node:test'
import assert from 'node:assert/strict'
import { MistralProvider } from '../server/chat/mistral-provider.ts'
test('Mistral adapter keeps text parts, finish reason, signal and no retry policy', async () => {
  const controller = new AbortController()
  let observed
  const client = {
    chat: {
      async stream(body, options) {
        observed = { body, options }
        return (async function* () {
          yield {
            data: {
              choices: [
                {
                  delta: {
                    content: [
                      { type: 'text', text: 'Olá' },
                      { type: 'image_url', imageUrl: 'x' },
                    ],
                  },
                  finishReason: null,
                },
              ],
            },
          }
          yield { data: { choices: [{ delta: {}, finishReason: 'length' }] } }
        })()
      },
    },
  }
  const provider = new MistralProvider(
    {
      apiKey: 'fixture-key-never-public',
      model: 'fixed-test',
      uiPrompt: 'UI instructions',
    },
    client
  )
  const events = []
  for await (const e of provider.stream({
    messages: [
      { role: 'system', content: 'approved' },
      { role: 'user', content: 'question' },
    ],
    signal: controller.signal,
  }))
    events.push(e)
  assert.deepEqual(events, [
    { type: 'delta', text: 'Olá' },
    { type: 'done', finishReason: 'length' },
  ])
  assert.equal(observed.body.model, 'fixed-test')
  assert.equal(observed.body.maxTokens, 1400)
  assert.equal(observed.options.signal, controller.signal)
  assert.equal(observed.options.retries.strategy, 'none')
  assert.match(observed.body.messages[0].content, /approved/)
  assert.match(observed.body.messages[0].content, /UI instructions/)
})
test('no key yields no synthetic response or fake done', async () => {
  const p = new MistralProvider({ model: 'test', uiPrompt: '' })
  await assert.rejects(async () => {
    for await (const _ of p.stream({
      messages: [],
      signal: new AbortController().signal,
    }))
      assert.fail('no events')
  })
})
