export type ProviderMessage = {
  role: 'system' | 'user' | 'assistant'
  content: string
}
export type ProviderEvent =
  | { type: 'delta'; text: string }
  | { type: 'done'; finishReason: 'stop' | 'length' | 'other' }
export interface ChatProvider {
  stream(input: {
    messages: ProviderMessage[]
    signal: AbortSignal
  }): AsyncIterable<ProviderEvent>
}
