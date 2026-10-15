import { lazy, Suspense } from 'react'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { CommunicationSection } from './components/CommunicationSection'
import { AppSection } from './components/AppSection'
import { AudienceSection } from './components/AudienceSection'
import { FaqSection } from './components/FaqSection'
import { Footer } from './components/Footer'
import { IntroProvider, useIntroState } from './intro/IntroProvider'

const ChatWidget = lazy(() =>
  import('./features/chatbot/ChatWidget').then((module) => ({
    default: module.ChatWidget,
  }))
)

function ChatEntry() {
  const { complete } = useIntroState()
  return complete ? (
    <Suspense fallback={null}>
      <ChatWidget />
    </Suspense>
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
