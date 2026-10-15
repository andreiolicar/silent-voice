import './openui-bootstrap'
import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import type { ChatTransport } from './chat-client'
import { LoadBoundary } from '../../components/LoadBoundary'
import './chat-widget.css'
const ChatPanel = lazy(() => import('./ChatPanel'))
export function ChatWidget({
  ready = true,
  transport,
}: {
  ready?: boolean
  transport?: ChatTransport
}) {
  const [open, setOpen] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const launcher = useRef<HTMLButtonElement>(null)
  const minimize = useCallback(() => {
    setOpen(false)
    launcher.current?.focus()
  }, [])
  useEffect(() => {
    if (!open) return
    const handle = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        minimize()
      }
    }
    document.addEventListener('keydown', handle)
    return () => document.removeEventListener('keydown', handle)
  }, [open, minimize])
  if (!ready) return null
  return (
    <div id="silent-voice-chat">
      {loaded && (
        <LoadBoundary
          fallback={
            open ? (
              <section
                id="silent-voice-chat-panel"
                className="sv-chat-loading"
                role="dialog"
                aria-label="Assistente Silent Voice"
              >
                <p role="alert">
                  Não foi possível carregar o assistente. Recarregue a página ou
                  fale com a equipe.
                </p>
                <a href="mailto:contato@silentvoice.com.br">
                  contato@silentvoice.com.br
                </a>
              </section>
            ) : null
          }
        >
          <Suspense
            fallback={
              open ? (
                <div className="sv-chat-loading" role="status">
                  Carregando assistente…
                </div>
              ) : null
            }
          >
            <ChatPanel
              hidden={!open}
              onMinimize={minimize}
              transport={transport}
            />
          </Suspense>
        </LoadBoundary>
      )}
      <button
        ref={launcher}
        type="button"
        className="sv-chat-launcher"
        aria-label={
          open ? 'Fechar painel do assistente' : 'Abrir assistente Silent Voice'
        }
        aria-expanded={open}
        aria-controls="silent-voice-chat-panel"
        onClick={() => {
          if (open) minimize()
          else {
            setLoaded(true)
            setOpen(true)
          }
        }}
      >
        <span className="sv-chat-launcher-mark" aria-hidden="true" />
      </button>
    </div>
  )
}
