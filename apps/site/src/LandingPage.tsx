import { lazy, Suspense } from 'react'
import { LoadBoundary } from '@silent-voice/web-ui/LoadBoundary'
import { IntroProvider, useIntroState } from './intro/IntroProvider'
import { Header } from './components/Header'
import './styles/responsive.css'
import { Audience } from './v2/Audience'
import { ProductHero } from './v2/ProductHero'
import { Hero } from './v2/Hero'
import { AgentTeam } from './v2/AgentTeam'
import { Capabilities } from './v2/Capabilities'
import { Faq } from './v2/Faq'
import { Waitlist } from './v2/Waitlist'
import { LandingFooter } from './v2/LandingFooter'
import { usePageEntrance } from './v2/usePageEntrance'
import './v2/landing-v2.css'
const ChatWidget = lazy(() =>
  import('./features/chatbot/ChatWidget').then((module) => ({
    default: module.ChatWidget,
  })),
)
function ChatEntry() {
  const { complete } = useIntroState()
  return complete ? (
    <LoadBoundary
      fallback={
        <p
          role="alert"
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 80,
            maxWidth: 320,
            padding: 20,
            borderRadius: 24,
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
          }}
        >
          Não foi possível carregar o assistente. Fale com a equipe:{' '}
          <a href="mailto:contato@silentvoice.com.br">
            contato@silentvoice.com.br
          </a>
        </p>
      }
    >
      <Suspense fallback={null}>
        <ChatWidget />
      </Suspense>
    </LoadBoundary>
  ) : null
}

function LandingContent() {
  const entranceRef = usePageEntrance()
  return (
      <div className="sv-v2" ref={entranceRef}>
        <main id="conteudo" tabIndex={-1}>
          <ProductHero />
          <Audience />
          <Hero />
          <AgentTeam />
          <Capabilities />
          <Faq />
          <Waitlist />
        </main>
        <LandingFooter />
      </div>
  )
}

export function LandingPage() {
  return (
    <IntroProvider>
      <a className="skip-link" href="#conteudo">
        Pular para o conteúdo
      </a>
      <Header participateHref="#lista" />
      <LandingContent />
      <ChatEntry />
    </IntroProvider>
  )
}
