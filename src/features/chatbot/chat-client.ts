import type { ChatRequest, ChatStreamEvent } from '../../../shared/chat'
import { consumeChatStream } from './sse-parser'
import { waitForApi } from './api-readiness'
export type ChatTransport = (
  request: ChatRequest,
  signal: AbortSignal,
  onEvent: (event: ChatStreamEvent) => void
) => Promise<void>
export const streamChat: ChatTransport = async (request, signal, onEvent) => {
  await waitForApi(signal)
  signal.throwIfAborted()
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
  if (!response.ok)
    throw new Error(
      response.status === 429 ? 'rate_limited' : 'service_unavailable'
    )
  if (!response.headers.get('content-type')?.includes('text/event-stream'))
    throw new Error('invalid_stream')
  await consumeChatStream(response, signal, onEvent)
}
