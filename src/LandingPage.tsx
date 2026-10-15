import { lazy, Suspense } from 'react'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { CommunicationSection } from './components/CommunicationSection'
import { AppSection } from './components/AppSection'
import { AudienceSection } from './components/AudienceSection'
import { FaqSection } from './components/FaqSection'
import { Footer } from './components/Footer'
import { LoadBoundary } from './components/LoadBoundary'
import { IntroProvider, useIntroState } from './intro/IntroProvider'

const ChatWidget = lazy(() =>
  import('./features/chatbot/ChatWidget').then((module) => ({
    default: module.ChatWidget,
  }))
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

export function LandingPage() {
  return (
    <IntroProvider>
      <a className="skip-link" href="#hero-heading">
        Pular para o conteúdo
      </a>
      <Header />
      <main>
        <Hero />
        <CommunicationSection />
        <AppSection />
        <AudienceSection />
        <FaqSection />
      </main>
      <Footer />
      <ChatEntry />
    </IntroProvider>
  )
}
