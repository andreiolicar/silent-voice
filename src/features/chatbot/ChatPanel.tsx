import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowUpRight, ChevronDown, Minus, RotateCcw } from 'lucide-react'
import { ThemeProvider, createTheme } from '@openuidev/react-ui/ThemeProvider'
import type { ChatTransport } from './chat-client'
import { useChatConversation } from './useChatConversation'
import { ChatResponse } from './ChatResponse'
import { ChatLeadForm } from './ChatLeadForm'
import { ChatButton } from './ChatButton'
import { ChatComposer } from './ChatComposer'
const theme = createTheme({
  background: 'var(--color-surface)',
  foreground: 'var(--color-surface)',
  textNeutralPrimary: 'var(--color-text)',
  textNeutralSecondary: 'var(--color-text-muted)',
  textBrand: 'var(--sv-chat-accent)',
  interactiveAccentDefault: 'var(--color-brand)',
  interactiveAccentHover:
    'color-mix(in srgb, var(--color-brand) 88%, var(--color-ink))',
  interactiveAccentPressed:
    'color-mix(in srgb, var(--color-brand) 75%, var(--color-ink))',
  borderAccent: 'var(--color-border-accent)',
  fontBody: 'var(--font-sans)',
  fontHeading: 'var(--font-sans)',
  fontLabel: 'var(--font-sans)',
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
          <span className="sv-chat-brand" aria-hidden="true">
            <span className="sv-chat-brand-mark" />
          </span>
          <div>
            <h2 id="sv-chat-title"><span className="sv-sr-only">Assistente</span>{' '}Silent Voice</h2>
            <p>Assistente de IA</p>
          </div>
          <ChatButton
            tone="quiet"
            size="icon"
            className="sv-chat-minimize"
            aria-label="Minimizar assistente"
            onClick={onMinimize}
          >
            <Minus className="sv-chat-icon" size={16} strokeWidth={1.65} aria-hidden="true" />
          </ChatButton>
        </header>
        <nav className="sv-chat-toolbar" aria-label="Ações da conversa">
          <ChatButton tone="quiet" onClick={reset}>
            <RotateCcw className="sv-chat-icon" size={14} strokeWidth={1.65} aria-hidden="true" />
            Nova conversa
          </ChatButton>
          {mode === 'chat' ? (
            <ChatButton
              className="sv-chat-contact-button"
              onClick={openContact}
            >
              Falar com a equipe
              <ArrowUpRight className="sv-chat-icon" size={14} strokeWidth={1.65} aria-hidden="true" />
            </ChatButton>
          ) : (
            <ChatButton
              className="sv-chat-contact-button"
              onClick={() => setMode('chat')}
            >
              <ArrowLeft className="sv-chat-icon" size={14} strokeWidth={1.65} aria-hidden="true" />
              Voltar à conversa
            </ChatButton>
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
          {chat.messages.length === 0 && (
            <>
              <div className="sv-chat-greeting">
                <h3>Como podemos ajudar?</h3>
                <p>Tire suas dúvidas sobre o Silent Voice ou converse com nossa equipe.</p>
              </div>
              <div className="sv-chat-suggestions">
                {questions.map((question) => (
                  <ChatButton
                    key={question}
                    onClick={() => chat.send(question)}
                  >
                    {question}
                    <ArrowUpRight className="sv-chat-icon" size={14} strokeWidth={1.65} aria-hidden="true" />
                  </ChatButton>
                ))}
                <ChatButton onClick={openContact}>
                  Solicitar demonstração
                  <ArrowUpRight className="sv-chat-icon" size={14} strokeWidth={1.65} aria-hidden="true" />
                </ChatButton>
              </div>
            </>
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
                  <div className="sv-chat-message-author" aria-hidden="true">
                    <span className="sv-chat-brand-mark" />Silent Voice
                  </div>
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
                ? 'Preparando resposta…'
                : 'Respondendo…'}
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
                <ChatButton
                  tone="quiet"
                  onClick={() => {
                    chat.setDraft(lastQuestion)
                    composer.current?.focus()
                  }}
                >
                  Rever pergunta
                </ChatButton>
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
          <ChatComposer
            inputRef={composer}
            active={!hidden && mode === 'chat'}
            draft={chat.draft}
            busy={busy}
            onChange={chat.setDraft}
            onSend={chat.send}
            onStop={chat.stop}
          />
          <details className="sv-chat-privacy">
            <summary>Sobre a IA e seus dados<ChevronDown className="sv-chat-icon" size={12} strokeWidth={1.65} aria-hidden="true" /></summary>
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
