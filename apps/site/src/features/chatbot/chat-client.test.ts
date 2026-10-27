import { afterEach, describe, expect, it, vi } from 'vitest'
import { streamChat } from './chat-client'

const request = { requestId: 'cold-start', messages: [{ id: 'user-1', role: 'user' as const, content: 'Como funciona?' }] }
const ready = () => new Response('{"status":"ok"}', { headers: { 'Content-Type': 'application/json' } })
const answer = () => new Response([
  'data: {"type":"delta","requestId":"cold-start","text":"Olá"}\n\n',
  'data: {"type":"done","requestId":"cold-start","finishReason":"stop"}\n\n',
].join(''), { headers: { 'Content-Type': 'text/event-stream' } })

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

describe('chat transport after backend startup', () => {
  it('waits for a cold backend and sends the question exactly once after readiness', async () => {
    vi.useFakeTimers()
    const requests: string[] = []
    vi.stubGlobal('fetch', async (url: string) => {
      requests.push(url)
      if (url === '/api/health') {
        await new Promise(resolve => setTimeout(resolve, 60_000))
        return ready()
      }
      return answer()
    })
    const events: unknown[] = []
    const pending = streamChat(request, new AbortController().signal, event => events.push(event))
    await vi.advanceTimersByTimeAsync(30_000)
    expect(requests).toEqual(['/api/health'])
    expect(events).toEqual([])
    await vi.advanceTimersByTimeAsync(30_000)
    await pending
    expect(requests).toEqual(['/api/health', '/api/chat'])
    expect(events).toEqual([
      { type: 'delta', requestId: 'cold-start', text: 'Olá' },
      { type: 'done', requestId: 'cold-start', finishReason: 'stop' },
    ])
  })

  it('does not send the question if stopped during backend startup', async () => {
    vi.useFakeTimers()
    const requests: string[] = []
    vi.stubGlobal('fetch', async (url: string) => {
      requests.push(url)
      return new Response('', { status: 503 })
    })
    const controller = new AbortController()
    const pending = streamChat(request, controller.signal, () => {})
    const rejected = expect(pending).rejects.toThrow()
    await vi.advanceTimersByTimeAsync(0)
    controller.abort()
    await rejected
    await vi.advanceTimersByTimeAsync(5_000)
    expect(requests).toEqual(['/api/health'])
  })
})
