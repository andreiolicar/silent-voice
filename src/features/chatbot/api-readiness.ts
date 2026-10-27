/** Free hosting can serve an HTML loading page while the backend starts.
 * Poll only the read-only health route; never retry a message or submission here.
 */
export async function waitForApi(signal: AbortSignal): Promise<void> {
  signal.throwIfAborted()
  const controller = new AbortController()
  const cancel = () => controller.abort(signal.reason)
  signal.addEventListener('abort', cancel, { once: true })
  const deadline = setTimeout(() => controller.abort(new Error('service_start_timeout')), 90_000)
  const active = controller.signal
  try {
    while (true) {
      active.throwIfAborted()
      try {
        const response = await fetch('/api/health', { signal: active, cache: 'no-store' })
        if (response.ok && response.headers.get('content-type')?.includes('application/json')) {
          const body: unknown = await response.json()
          active.throwIfAborted()
          if (body && typeof body === 'object' && 'status' in body && body.status === 'ok') return
        } else await response.body?.cancel()
      } catch {
        active.throwIfAborted()
      }
      await new Promise<void>((resolve, reject) => {
        const abort = () => {
          clearTimeout(timer)
          reject(active.reason)
        }
        const timer = setTimeout(() => {
          active.removeEventListener('abort', abort)
          resolve()
        }, 1_000)
        active.addEventListener('abort', abort, { once: true })
        if (active.aborted) abort()
      })
    }
  } finally {
    clearTimeout(deadline)
    signal.removeEventListener('abort', cancel)
  }
}
