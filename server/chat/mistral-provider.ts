import { Mistral } from '@mistralai/mistralai'
import type {
  ChatProvider,
  ProviderEvent,
  ProviderMessage,
} from './provider.ts'
export class MistralProvider implements ChatProvider {
  private readonly client: Pick<Mistral, 'chat'> | undefined
  private readonly model: string
  private readonly uiPrompt: string
  constructor(
    options: { apiKey?: string; model: string; uiPrompt: string },
    client?: Pick<Mistral, 'chat'>
  ) {
    this.client =
      client ||
      (options.apiKey ? new Mistral({ apiKey: options.apiKey }) : undefined)
    this.model = options.model
    this.uiPrompt = options.uiPrompt
  }
  async *stream({
    messages,
    signal,
  }: {
    messages: ProviderMessage[]
    signal: AbortSignal
  }): AsyncIterable<ProviderEvent> {
    if (!this.client) throw new Error('Mistral is not configured')
    const system = messages
      .filter((m) => m.role === 'system')
      .map((m) => m.content)
      .join('\n')
    const stream = await this.client.chat.stream(
      {
        model: this.model,
        messages: [
          { role: 'system', content: `${system}\n\n${this.uiPrompt}` },
          ...messages.filter((m) => m.role !== 'system'),
        ],
        temperature: 0.2,
        maxTokens: 1400,
        responseFormat: { type: 'text' },
        stream: true,
      },
      { signal, retries: { strategy: 'none' } }
    )
    for await (const event of stream) {
      const choice = event.data.choices?.[0]
      if (!choice) continue
      const content = choice.delta?.content
      if (typeof content === 'string' && content)
        yield { type: 'delta', text: content }
      else if (Array.isArray(content)) {
        for (const part of content) {
          if (part.type === 'text' && typeof part.text === 'string')
            yield { type: 'delta', text: part.text }
        }
      }
      if (choice.finishReason) {
        yield {
          type: 'done',
          finishReason:
            choice.finishReason === 'stop'
              ? 'stop'
              : choice.finishReason === 'length'
                ? 'length'
                : 'other',
        }
        return
      }
    }
  }
}
