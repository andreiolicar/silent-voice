import { useState } from 'react'
import { Typography } from '@silent-voice/web-ui/Typography'
import type { AgentId } from './agents'
import { useIntroState } from '../intro/IntroProvider'
import { HumanHeroScene } from './HumanHeroScene'
import './product-hero.css'

/** Human-led opening with the three signal sources visible together. */
export function ProductHero({ onSelectAgent }: { onSelectAgent?: (id: AgentId) => void }) {
  const intro = useIntroState()
  const [interacted, setInteracted] = useState(false)
  const immediate = intro.immediate || interacted

  return (
    <section className="v2-product-hero" id="inicio" aria-labelledby="product-heading"
      data-ready={intro.ready} data-immediate={immediate}
      onFocusCapture={() => setInteracted(true)}>
      <div className="v2-product-copy">
        <Typography as="h1" variant="h1" id="product-heading" data-hero-enter="heading">
          O que você quer dizer merece ser ouvido.
        </Typography>
        <Typography as="p" variant="body" className="v2-product-description" data-hero-enter="description">
          Uma neckband que combina sinais musculares, movimentos dos lábios e contexto da conversa para ajudar a transformar sua expressão em voz.
        </Typography>
        <a className="v2-button v2-button--gradient" href="#lista" data-hero-enter="cta">
          Faça parte dessa nova voz
        </a>
      </div>

      <div className="v2-product-showcase">
        <div className="v2-product-glow" data-hero-enter="glow" aria-hidden="true" />
        <HumanHeroScene ready={intro.ready} immediate={immediate} onSelectAgent={onSelectAgent} />
      </div>
    </section>
  )
}
