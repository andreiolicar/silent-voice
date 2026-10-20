import type { ChatProvider, ProviderEvent, ProviderMessage } from './provider.ts'

type CompletionChunk = {
  error?: unknown
  choices?: Array<{
    delta?: { content?: unknown }
    finish_reason?: string | null
  }>
}

export class ZaiProvider implements ChatProvider {
  private readonly apiKey: string | undefined
  private readonly model: string
  private readonly uiPrompt: string
  private readonly fetcher: typeof fetch

  constructor(
    options: { apiKey?: string; model: string; uiPrompt: string },
    fetcher: typeof fetch = fetch
  ) {
    this.apiKey = options.apiKey
    this.model = options.model
    this.uiPrompt = options.uiPrompt
    this.fetcher = fetcher
  }

  async *stream({ messages, signal }: {
    messages: ProviderMessage[]
    signal: AbortSignal
  }): AsyncIterable<ProviderEvent> {
    if (!this.apiKey) throw new Error('Z.ai is not configured')
    signal.throwIfAborted()
    const system = messages.filter(message => message.role === 'system')
      .map(message => message.content).join('\n')
    const response = await this.fetcher('https://api.z.ai/api/paas/v4/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: 'system', content: `${system}\n\n${this.uiPrompt}` },
          ...messages.filter(message => message.role !== 'system'),
        ],
        stream: true,
        thinking: { type: 'disabled' },
        max_tokens: 2048,
      }),
      signal,
    })
    if (!response.ok) {
      await response.body?.cancel().catch(() => {})
      throw Object.assign(new Error('Z.ai request failed'), { status: response.status })
    }
    if (!response.body) throw new Error('Empty Z.ai stream')
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8', { fatal: true })
    let buffer = ''
    let bytes = 0
    const cancel = () => { void reader.cancel().catch(() => {}) }
    signal.addEventListener('abort', cancel, { once: true })
    try {
      signal.throwIfAborted()
      while (true) {
        const { value, done } = await reader.read()
        signal.throwIfAborted()
        // A closed transport alone is not a confirmed model completion.
        if (done) return
        bytes += value.byteLength
        if (bytes > 512000) throw new Error('Z.ai stream too large')
        buffer += decoder.decode(value, { stream: true })
        if (buffer.length > 70000) throw new Error('Z.ai frame too large')
        let boundary: RegExpExecArray | null
        while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
          const frame = buffer.slice(0, boundary.index)
          buffer = buffer.slice(boundary.index + boundary[0].length)
          const data = frame.split(/\r?\n/)
            .filter(line => line.startsWith('data:'))
            .map(line => line.slice(5).replace(/^ /, '')).join('\n')
          if (!data) continue
          if (data === '[DONE]') return
          const event = JSON.parse(data) as CompletionChunk | null
          if (!event || typeof event !== 'object' || event.error)
            throw new Error('Invalid Z.ai stream event')
          const choice = event.choices?.[0]
          const text = choice?.delta?.content
          // reasoning_content, tools and other non-text fields stay private.
          if (typeof text === 'string' && text) yield { type: 'delta', text }
          if (choice?.finish_reason) {
            yield {
              type: 'done',
              finishReason: choice.finish_reason === 'stop' ? 'stop'
                : choice.finish_reason === 'length' ? 'length' : 'other',
            }
            return
          }
        }
      }
    } finally {
      signal.removeEventListener('abort', cancel)
      await reader.cancel().catch(() => {})
      reader.releaseLock()
    }
  }
}
