import { afterEach, describe, expect, it, vi } from 'vitest'
import { waitForApi } from './readiness'

const healthy = () => new Response('{"status":"ok"}', {
  headers: { 'Content-Type': 'application/json' },
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('API readiness on free hosting', () => {
  it('waits through the hosting loading page and a minute-long cold start', async () => {
    vi.useFakeTimers()
    let attempts = 0
    vi.stubGlobal('fetch', async () => {
      attempts++
      if (attempts === 1) return new Response('<html>Starting service</html>')
      if (attempts === 2) return new Response('Unavailable', { status: 503 })
      await new Promise(resolve => setTimeout(resolve, 60_000))
      return healthy()
    })
    let ready = false
    const pending = waitForApi(new AbortController().signal).then(() => { ready = true })
    await vi.advanceTimersByTimeAsync(30_000)
    expect(ready).toBe(false)
    await vi.advanceTimersByTimeAsync(33_000)
    await pending
    expect(ready).toBe(true)
  })

  it('stops retrying when the caller cancels', async () => {
    vi.useFakeTimers()
    const aborter = new AbortController()
    const fetcher = vi.fn(async () => new Response('', { status: 503 }))
    vi.stubGlobal('fetch', fetcher)
    const pending = waitForApi(aborter.signal)
    const rejected = expect(pending).rejects.toThrow()
    await vi.advanceTimersByTimeAsync(0)
    aborter.abort()
    await rejected
    const attempts = fetcher.mock.calls.length
    await vi.advanceTimersByTimeAsync(10_000)
    expect(fetcher).toHaveBeenCalledTimes(attempts)
  })

  it('bounds the wait even when the readiness response stalls', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', (_url: string, init: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init.signal!.addEventListener('abort', () => reject(init.signal!.reason), { once: true })
    }))
    const pending = waitForApi(new AbortController().signal)
    const rejected = expect(pending).rejects.toThrow()
    await vi.advanceTimersByTimeAsync(90_000)
    await rejected
  })
})
