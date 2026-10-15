import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChatMessage } from '../../../shared/chat'
import { streamChat } from './chat-client'
import type { ChatTransport } from './chat-client'
export type ChatPhase =
  'idle' | 'sending' | 'receiving' | 'complete' | 'stopped' | 'error'
export function useChatConversation(transport: ChatTransport = streamChat) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [phase, setPhase] = useState<ChatPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const current = useRef({
    messages: [] as ChatMessage[],
    epoch: 0,
    controller: null as AbortController | null,
    mounted: true,
  })
  useEffect(() => {
    current.current.mounted = true
    return () => {
      current.current.mounted = false
      current.current.epoch++
      current.current.controller?.abort()
    }
  }, [])
  const stop = useCallback(() => {
    current.current.epoch++
    current.current.controller?.abort()
    current.current.controller = null
    setPhase('stopped')
  }, [])
  const reset = useCallback(() => {
    current.current.epoch++
    current.current.controller?.abort()
    current.current.controller = null
    current.current.messages = []
    setMessages([])
    setPhase('idle')
    setError(null)
    setDraft('')
  }, [])
  const send = useCallback(
    (value?: string) => {
      const text = (value ?? draft).trim()
      const state = current.current
      if (!text || text.length > 2000 || state.controller) return
      state.controller = new AbortController()
      const controller = state.controller
      const epoch = ++state.epoch
      const requestId = crypto.randomUUID()
      const assistantId = crypto.randomUUID()
      // Keep all visible history in memory; send only a bounded recent context.
      const user: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
      }
      const visible = [...state.messages, user]
      state.messages = visible
      setMessages(visible)
      setDraft('')
      setError(null)
      setPhase('sending')
      const history = visible.slice(-16)
      while (
        history.length > 1 &&
        (history.reduce((n, m) => n + m.content.length, 0) > 16000 ||
          history.some((m) => m.content.length > 8000))
      )
        history.shift()
      const active = () =>
        state.mounted && state.epoch === epoch && !controller.signal.aborted
      let finalized = false
      void transport(
        { requestId, messages: history },
        controller.signal,
        (event) => {
          if (!active() || event.requestId !== requestId) return
          if (event.type === 'delta') {
            setPhase('receiving')
            const existing = state.messages.find((m) => m.id === assistantId)
            state.messages = existing
              ? state.messages.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + event.text }
                    : m
                )
              : [
                  ...state.messages,
                  { id: assistantId, role: 'assistant', content: event.text },
                ]
            setMessages(state.messages)
          } else if (event.type === 'done') {
            finalized = true
            if (
              !state.messages.find((m) => m.id === assistantId)?.content.trim()
            ) {
              setPhase('error')
              setError(
                'Não recebemos uma resposta. Tente novamente ou converse com a equipe.'
              )
              return
            }
            setPhase('complete')
            if (event.finishReason === 'length')
              setError(
                'A resposta atingiu o limite. Você pode fazer uma pergunta mais específica.'
              )
          } else {
            finalized = true
            setPhase('error')
            setError(
              'Não foi possível concluir a resposta. Você ainda pode conversar com a equipe.'
            )
          }
        }
      )
        .then(() => {
          if (active() && !finalized) {
            setPhase('error')
            setError('A resposta foi interrompida. Tente novamente.')
          }
        })
        .catch((cause) => {
          if (!active()) return
          setPhase('error')
          setError(
            cause instanceof Error && cause.message === 'rate_limited'
              ? 'Muitas mensagens em pouco tempo. Aguarde um momento e tente novamente.'
              : 'O assistente está indisponível no momento. Você pode registrar seu interesse ou usar nosso e-mail.'
          )
        })
        .finally(() => {
          if (state.epoch === epoch) state.controller = null
        })
    },
    [draft, transport]
  )
  return { messages, phase, error, draft, setDraft, send, stop, reset }
}
