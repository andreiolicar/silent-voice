import { LazyMotion, domAnimation } from 'motion/react'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { CommunicationSection } from './components/CommunicationSection'
import { AppSection } from './components/AppSection'
import { AudienceSection } from './components/AudienceSection'
import { FaqSection } from './components/FaqSection'
import { Footer } from './components/Footer'
import { IntroProvider } from './intro/IntroProvider'

export function App() {
  return (
    <LazyMotion features={domAnimation} strict>
      <IntroProvider>
        <a className="skip-link" href="#hero-heading">Pular para o conteúdo</a>
        <Header />
        <main>
          <Hero />
          <CommunicationSection />
          <AppSection />
          <AudienceSection />
          <FaqSection />
        </main>
        <Footer />
      </IntroProvider>
    </LazyMotion>
  )
}
