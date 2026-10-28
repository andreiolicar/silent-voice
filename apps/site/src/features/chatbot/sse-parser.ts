import type { ChatStreamEvent } from '@silent-voice/contracts/chat'
function parseEvent(data: string): ChatStreamEvent {
  const value: unknown = JSON.parse(data)
  if (!value || typeof value !== 'object') throw new Error('invalid_event')
  const e = value as Record<string, unknown>
  if (typeof e.requestId !== 'string' || e.requestId.length > 100)
    throw new Error('invalid_event')
  if (e.type === 'delta' && typeof e.text === 'string')
    return e as ChatStreamEvent
  if (
    e.type === 'done' &&
    (e.finishReason === 'stop' || e.finishReason === 'length')
  )
    return e as ChatStreamEvent
  if (
    e.type === 'error' &&
    typeof e.code === 'string' &&
    typeof e.retryable === 'boolean'
  )
    return e as ChatStreamEvent
  throw new Error('invalid_event')
}
export async function consumeChatStream(
  response: Response,
  signal: AbortSignal,
  onEvent: (event: ChatStreamEvent) => void
) {
  if (!response.body) throw new Error('empty_stream')
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8', { fatal: true })
  let buffer = ''
  let ended = false
  let bytes = 0
  const cancel = () => {
    void reader.cancel().catch(() => {})
  }
  signal.addEventListener('abort', cancel, { once: true })
  try {
    if (signal.aborted) throw new DOMException('Aborted', 'AbortError')
    while (!ended) {
      const { value, done } = await reader.read()
      if (signal.aborted) throw new DOMException('Aborted', 'AbortError')
      if (done) throw new Error('stream_interrupted')
      bytes += value.byteLength
      if (bytes > 512000) throw new Error('stream_too_large')
      buffer += decoder.decode(value, { stream: true })
      if (buffer.length > 70000) throw new Error('frame_too_large')
      let boundary: RegExpExecArray | null
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const frame = buffer.slice(0, boundary.index)
        buffer = buffer.slice(boundary.index + boundary[0].length)
        const data = frame
          .split(/\r?\n/)
          .filter((l) => l.startsWith('data:'))
          .map((l) => l.slice(5).replace(/^ /, ''))
          .join('\n')
        if (!data) continue
        const event = parseEvent(data)
        onEvent(event)
        if (event.type === 'done' || event.type === 'error') {
          ended = true
          break
        }
      }
    }
  } finally {
    signal.removeEventListener('abort', cancel)
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
