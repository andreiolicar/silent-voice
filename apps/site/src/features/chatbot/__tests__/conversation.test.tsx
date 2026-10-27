import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useChatConversation } from '../useChatConversation'
import type { ChatTransport } from '../chat-client'
import type { ChatRequest, ChatStreamEvent } from '../../../../shared/chat'
function controlled() {
  const pending: Array<{
    request: ChatRequest
    signal: AbortSignal
    emit: (e: ChatStreamEvent) => void
    end: () => void
  }> = []
  const transport: ChatTransport = (request, signal, emit) =>
    new Promise<void>((end) => pending.push({ request, signal, emit, end }))
  return { pending, transport }
}
describe('conversation lifecycle', () => {
  it('reset discards late network events and cannot attach them to the next conversation', async () => {
    const { pending, transport } = controlled()
    const { result } = renderHook(() => useChatConversation(transport))
    act(() => result.current.send('Como funciona?'))
    const first = pending[0]
    act(() => result.current.reset())
    expect(first.signal.aborted).toBe(true)
    act(() => result.current.send('E o app?'))
    act(() => {
      first.emit({
        type: 'delta',
        requestId: first.request.requestId,
        text: 'old answer',
      })
      first.end()
    })
    expect(result.current.messages.map((m) => m.content)).toEqual(['E o app?'])
    const next = pending[1]
    act(() => {
      next.emit({
        type: 'delta',
        requestId: next.request.requestId,
        text: 'new answer',
      })
      next.emit({
        type: 'done',
        requestId: next.request.requestId,
        finishReason: 'stop',
      })
      next.end()
    })
    await waitFor(() => expect(result.current.phase).toBe('complete'))
    expect(result.current.messages.at(-1)?.content).toBe('new answer')
  })
  it('stopping aborts but keeps the real partial response; wrong request deltas are ignored', async () => {
    const { pending, transport } = controlled()
    const { result, unmount } = renderHook(() => useChatConversation(transport))
    act(() => result.current.send('O que é?'))
    const p = pending[0]
    act(() => {
      p.emit({ type: 'delta', requestId: 'another-request', text: 'evil' })
      p.emit({ type: 'delta', requestId: p.request.requestId, text: 'partial' })
    })
    act(() => result.current.stop())
    expect(p.signal.aborted).toBe(true)
    expect(result.current.phase).toBe('stopped')
    expect(result.current.messages.at(-1)?.content).toBe('partial')
    unmount()
    p.end()
  })
  it('transport ending without done is an error, not a success', async () => {
    const { pending, transport } = controlled()
    const { result } = renderHook(() => useChatConversation(transport))
    act(() => result.current.send('Olá'))
    act(() => pending[0].end())
    await waitFor(() => expect(result.current.phase).toBe('error'))
    expect(result.current.error).toBeTruthy()
  })
  it('ignores empty input and concurrent send, and aborts the active request on unmount', () => {
    const { pending, transport } = controlled()
    const { result, unmount } = renderHook(() => useChatConversation(transport))
    act(() => result.current.send(' '))
    expect(result.current.messages).toHaveLength(0)
    act(() => result.current.send('Olá'))
    act(() => result.current.send('Outro'))
    expect(result.current.messages).toHaveLength(1)
    unmount()
    expect(pending[0].signal.aborted).toBe(true)
    pending[0].end()
  })
})

it('does not announce an empty completion as a successful answer', async () => {
  const { pending, transport } = controlled()
  const { result } = renderHook(() => useChatConversation(transport))
  act(() => result.current.send('Olá'))
  const p = pending[0]
  act(() => {
    p.emit({
      type: 'done',
      requestId: p.request.requestId,
      finishReason: 'stop',
    })
    p.end()
  })
  await waitFor(() => expect(result.current.phase).toBe('error'))
  expect(result.current.error).toBeTruthy()
})
