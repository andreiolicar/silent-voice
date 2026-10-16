import { useLayoutEffect } from 'react'
import type { RefObject } from 'react'
import { ArrowUp, Square } from 'lucide-react'
import { ChatButton } from './ChatButton'
import './chat-composer.css'

type ChatComposerProps = {
  inputRef: RefObject<HTMLTextAreaElement | null>
  active: boolean
  draft: string
  busy: boolean
  onChange: (value: string) => void
  onSend: () => void
  onStop: () => void
}

export function ChatComposer({ inputRef, active, draft, busy, onChange, onSend, onStop }: ChatComposerProps) {
  useLayoutEffect(() => {
    const input = inputRef.current
    if (!active || !input) return
    const resize = () => {
      input.style.height = '0px'
      const height = Math.max(24, Math.min(input.scrollHeight, 96))
      input.style.height = `${height}px`
      input.style.overflowY = input.scrollHeight > 96 ? 'auto' : 'hidden'
    }
    resize()
    let width = input.clientWidth
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => {
      if (input.clientWidth === width) return
      width = input.clientWidth
      resize()
    })
    observer?.observe(input)
    window.addEventListener('resize', resize)
    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', resize)
    }
  }, [active, draft, inputRef])

  return (
    <form className="sv-chat-composer" onSubmit={event => {
      event.preventDefault()
      if (!busy) onSend()
    }}>
      <label className="sv-sr-only" htmlFor="sv-chat-message">Sua mensagem</label>
      <textarea
        ref={inputRef}
        id="sv-chat-message"
        rows={1}
        value={draft}
        maxLength={2000}
        placeholder="Escreva sua dúvida…"
        onChange={event => onChange(event.target.value)}
        onKeyDown={event => {
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) {
            event.preventDefault()
            if (!busy) onSend()
          }
        }}
      />
      <div className="sv-chat-composer-actions">
        <span aria-hidden="true">{draft.length > 0 ? `${draft.length}/2000` : ''}</span>
        {busy ? (
          <ChatButton size="icon" aria-label="Parar resposta" onClick={onStop}>
            <Square className="sv-chat-icon" size={14} fill="currentColor" strokeWidth={0} aria-hidden="true" />
          </ChatButton>
        ) : (
          <ChatButton type="submit" tone="green" size="icon" aria-label="Enviar mensagem" disabled={!draft.trim()}>
            <ArrowUp className="sv-chat-icon" size={16} strokeWidth={1.75} aria-hidden="true" />
          </ChatButton>
        )}
      </div>
    </form>
  )
}
