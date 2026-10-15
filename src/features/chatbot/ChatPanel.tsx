import { useEffect, useRef, useState } from 'react'
import { ThemeProvider, createTheme } from '@openuidev/react-ui/ThemeProvider'
import type { ChatTransport } from './chat-client'
import { useChatConversation } from './useChatConversation'
import { ChatResponse } from './ChatResponse'
import { ChatLeadForm } from './ChatLeadForm'
const theme = createTheme({
  background: 'var(--color-surface, #fff)',
  foreground: 'var(--color-surface, #fff)',
  textNeutralPrimary: 'var(--color-ink, #051b34)',
  textNeutralSecondary: 'var(--color-text-muted, #536272)',
  textBrand: 'var(--sv-chat-accent)',
  interactiveAccentDefault: 'var(--color-brand, #1aa99b)',
  interactiveAccentHover:
    'color-mix(in srgb, var(--color-brand, #1aa99b) 88%, var(--color-ink, #051b34))',
  interactiveAccentPressed:
    'color-mix(in srgb, var(--color-brand, #1aa99b) 75%, var(--color-ink, #051b34))',
  borderAccent: 'var(--color-brand, #1aa99b)',
  fontBody: 'Inter Variable, Inter, sans-serif',
  fontHeading: 'Inter Variable, Inter, sans-serif',
  fontLabel: 'Inter Variable, Inter, sans-serif',
})
const questions = [
  'O que é o Silent Voice?',
  'Como o dispositivo funciona?',
  'O que posso ver no aplicativo?',
]
export default function ChatPanel({
  hidden,
  onMinimize,
  transport,
}: {
  hidden: boolean
  onMinimize: () => void
  transport?: ChatTransport
}) {
  const chat = useChatConversation(transport)
  const [mode, setMode] = useState<'chat' | 'contact'>('chat')
  const [hasContact, setHasContact] = useState(false)
  const [leadVersion, setLeadVersion] = useState(0)
  const composer = useRef<HTMLTextAreaElement>(null)
  const contact = useRef<HTMLDivElement>(null)
  const scroll = useRef<HTMLDivElement>(null)
  const followOutput = useRef(true)
  const busy = chat.phase === 'sending' || chat.phase === 'receiving'
  useEffect(() => {
    if (hidden) return
    if (mode === 'chat') composer.current?.focus()
    else contact.current?.querySelector<HTMLElement>('input, [data-contact-receipt]')?.focus()
  }, [hidden, mode, leadVersion])
  useEffect(() => {
    if (!scroll.current || hidden || mode !== 'chat') return
    if (chat.messages.length === 0) {
      scroll.current.scrollTop = 0
      followOutput.current = true
    } else if (followOutput.current)
      scroll.current.scrollTop = scroll.current.scrollHeight
  }, [chat.messages, chat.phase, hidden, mode])
  const openContact = () => {
    setHasContact(true)
    setMode('contact')
  }
  const reset = () => {
    chat.reset()
    setLeadVersion((v) => v + 1)
    setHasContact(false)
    setMode('chat')
  }
  const lastQuestion = [...chat.messages]
    .reverse()
    .find((message) => message.role === 'user')?.content
  return (
    <ThemeProvider
      cssSelector="#silent-voice-chat"
      mode="light"
      lightTheme={theme}
    >
      <section
        id="silent-voice-chat-panel"
        className="sv-chat-panel"
        role="dialog"
        aria-modal="false"
        aria-labelledby="sv-chat-title"
        hidden={hidden}
        inert={hidden}
      >
        <header className="sv-chat-header">
          <span className="sv-chat-brand">
            <img src="/assets/icone.svg" width="28" height="28" alt="" />
          </span>
          <div>
            <h2 id="sv-chat-title">Assistente Silent Voice</h2>
            <p>
              <span className="sv-ai-badge">IA</span> Para conhecer e conectar
            </p>
          </div>
          <button
            type="button"
            className="sv-chat-icon-button"
            aria-label="Minimizar assistente"
            onClick={onMinimize}
          >
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M6 12h12"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </header>
        <nav className="sv-chat-toolbar" aria-label="Ações da conversa">
          <button type="button" onClick={reset}>
            Nova conversa
          </button>
          {mode === 'chat' ? (
            <button
              type="button"
              className="sv-chat-contact-button"
              onClick={openContact}
            >
              Falar com a equipe <span aria-hidden="true">↗</span>
            </button>
          ) : (
            <button
              type="button"
              className="sv-chat-contact-button"
              onClick={() => setMode('chat')}
            >
              Voltar à conversa <span aria-hidden="true">↩</span>
            </button>
          )}
        </nav>
        <div
          ref={scroll}
          className="sv-chat-scroll"
          onScroll={(event) => {
            const viewport = event.currentTarget
            followOutput.current =
              viewport.scrollHeight -
                viewport.scrollTop -
                viewport.clientHeight <
              64
          }}
          hidden={mode !== 'chat'}
          inert={mode !== 'chat'}
        >
          <div className="sv-chat-greeting">
            <span className="sv-chat-eyebrow">Olá, como podemos ajudar?</span>
            <h3>Vamos dar voz às suas dúvidas.</h3>
            <p>
              Posso explicar como funciona e ajudar você a conversar com a
              equipe. O que gostaria de saber?
            </p>
          </div>
          {chat.messages.length === 0 && (
            <div className="sv-chat-suggestions">
              {questions.map((question) => (
                <button
                  type="button"
                  key={question}
                  onClick={() => chat.send(question)}
                >
                  {question}
                  <span aria-hidden="true">↗</span>
                </button>
              ))}
              <button type="button" onClick={openContact}>
                Solicitar demonstração<span aria-hidden="true">↗</span>
              </button>
            </div>
          )}
          <div className="sv-chat-messages" aria-label="Mensagens da conversa">
            {chat.messages.map((message, index) =>
              message.role === 'user' ? (
                <div className="sv-chat-user-message" key={message.id}>
                  <span className="sv-sr-only">Você: </span>
                  {message.content}
                </div>
              ) : (
                <div className="sv-chat-assistant-message" key={message.id}>
                  <span className="sv-sr-only">Assistente IA: </span>
                  <ChatResponse
                    content={message.content}
                    streaming={busy && index === chat.messages.length - 1}
                    interrupted={index === chat.messages.length - 1 && (chat.phase === 'stopped' || chat.phase === 'error' || (chat.phase === 'complete' && !!chat.error))}
                    onContact={openContact}
                  />
                </div>
              )
            )}
          </div>
          {busy && (
            <p className="sv-chat-progress" aria-label="Resposta em andamento">
              <span aria-hidden="true" />
              {chat.phase === 'sending'
                ? 'Enviando sua pergunta…'
                : 'Recebendo resposta…'}
            </p>
          )}
          {chat.phase === 'stopped' && (
            <p className="sv-chat-notice">
              Resposta interrompida. Você pode fazer outra pergunta.
            </p>
          )}
          {chat.error && (
            <div className="sv-chat-error" role="alert">
              <p>{chat.error}</p>
              {lastQuestion && (
                <button
                  type="button"
                  onClick={() => {
                    chat.setDraft(lastQuestion)
                    composer.current?.focus()
                  }}
                >
                  Rever pergunta
                </button>
              )}
            </div>
          )}
        </div>
        {hasContact && (
          <div
            ref={contact}
            className="sv-chat-scroll sv-contact-scroll"
            hidden={mode !== 'contact'}
            inert={mode !== 'contact'}
          >
            <ChatLeadForm key={leadVersion} />
          </div>
        )}
        <div
          className="sv-chat-bottom"
          hidden={mode !== 'chat'}
          inert={mode !== 'chat'}
        >
          <form
            className="sv-chat-composer"
            onSubmit={(event) => {
              event.preventDefault()
              chat.send()
            }}
          >
            <label className="sv-sr-only" htmlFor="sv-chat-message">
              Sua mensagem
            </label>
            <textarea
              ref={composer}
              id="sv-chat-message"
              rows={2}
              value={chat.draft}
              maxLength={2000}
              placeholder="Escreva sua dúvida…"
              onChange={(event) => chat.setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (
                  event.key === 'Enter' &&
                  !event.shiftKey &&
                  !event.nativeEvent.isComposing &&
                  event.keyCode !== 229
                ) {
                  event.preventDefault()
                  if (!busy) chat.send()
                }
              }}
            />
            <div className="sv-chat-composer-actions">
              <span>{chat.draft.length}/2000</span>
              {busy ? (
                <button
                  type="button"
                  className="sv-chat-stop"
                  aria-label="Parar resposta"
                  onClick={chat.stop}
                >
                  <span aria-hidden="true">■</span> Parar
                </button>
              ) : (
                <button
                  type="submit"
                  className="sv-chat-send"
                  aria-label="Enviar mensagem"
                  disabled={!chat.draft.trim()}
                >
                  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M12 18V6m-5 5 5-5 5 5"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              )}
            </div>
          </form>
          <details className="sv-chat-privacy">
            <summary>Sobre a IA e seus dados</summary>
            <p>
              O texto da conversa é enviado ao provedor de IA Mistral para gerar
              respostas. A IA pode cometer erros. Evite dados clínicos e outras
              informações sensíveis. O formulário de contato é separado e seus
              campos não são enviados automaticamente à IA.
            </p>
          </details>
          <a className="sv-chat-email" href="mailto:contato@silentvoice.com.br">
            contato@silentvoice.com.br
          </a>
        </div>
        <div className="sv-sr-only" role="status" aria-live="polite">
          {chat.phase === 'complete'
            ? chat.error ? 'Resposta limitada. Você pode fazer outra pergunta.' : 'Resposta concluída.'
            : chat.phase === 'stopped'
              ? 'Resposta interrompida.'
              : ''}
        </div>
      </section>
    </ThemeProvider>
  )
}
