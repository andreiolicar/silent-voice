export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
}
export type ChatRequest = { requestId: string; messages: ChatMessage[] }
export type ChatStreamEvent =
  | { type: 'delta'; requestId: string; text: string }
  | { type: 'done'; requestId: string; finishReason: 'stop' | 'length' }
  | { type: 'error'; requestId: string; code: string; retryable: boolean }
