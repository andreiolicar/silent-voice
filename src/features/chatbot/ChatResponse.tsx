import { Component, useEffect, useMemo, useState, type ReactNode } from 'react'
import { createParser, Renderer, type ElementNode } from '@openuidev/react-lang'
import { ContactContext, silentVoiceLibrary } from './response-library'
import '@openuidev/react-ui/styles/card.css'
import '@openuidev/react-ui/styles/button.css'
import '@openuidev/react-ui/styles/steps.css'

const parser = createParser(silentVoiceLibrary.toJSONSchema(), 'Answer')
const allowed = new Set(['Text', 'HowTo', 'BulletList', 'ContactAction'])
const fallback = (
  <p className="sv-chat-notice" role="status">
    Não foi possível exibir esta resposta. Tente perguntar novamente ou converse
    com a equipe.
  </p>
)
class ResponseBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    return this.state.failed ? fallback : this.props.children
  }
}
function renderable(root: ElementNode | null) {
  if (
    root?.typeName !== 'Answer' ||
    typeof root.props.title !== 'string' ||
    !Array.isArray(root.props.children) ||
    !root.props.children.length
  )
    return false
  const children = root.props.children as ElementNode[]
  const supported = children.every(
    (child) =>
      !!child && typeof child === 'object' && allowed.has(child.typeName)
  )
  const visible =
    root.props.title.trim().length > 0 ||
    children.some((child) => {
      if (!child?.props) return false
      if (child.typeName === 'ContactAction') return true
      if (child.typeName === 'Text')
        return (
          typeof child.props.text === 'string' &&
          child.props.text.trim().length > 0
        )
      return Array.isArray(child.props.items) && child.props.items.length > 0
    })
  return supported && visible
}
export function ChatResponse({
  content,
  streaming = false,
  interrupted = false,
  onContact,
}: {
  content: string
  streaming?: boolean
  interrupted?: boolean
  onContact: () => void
}) {
  // Keep this message's interruption state when a later question starts.
  const [wasInterrupted, setWasInterrupted] = useState(interrupted)
  useEffect(() => {
    if (interrupted) setWasInterrupted(true)
  }, [interrupted])
  const allowPartial = interrupted || wasInterrupted
  const valid = useMemo(() => {
    try {
      const result = parser.parse(content)
      return (
        renderable(result.root) &&
        (!result.meta.incomplete || allowPartial) &&
        result.meta.errors.length === 0 &&
        result.meta.unresolved.length === 0 &&
        result.queryStatements.length === 0 &&
        result.mutationStatements.length === 0
      )
    } catch {
      return false
    }
  }, [content, allowPartial])
  if (!streaming && !valid) return fallback
  return (
    <ContactContext.Provider value={onContact}>
      <ResponseBoundary key={content.length ? 'response' : 'empty'}>
        <Renderer
          response={content}
          library={silentVoiceLibrary}
          isStreaming={streaming}
          toolProvider={null}
          publishObservability={false}
        />
      </ResponseBoundary>
    </ContactContext.Provider>
  )
}
