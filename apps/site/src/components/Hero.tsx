import * as m from 'motion/react-m'
import { GreenButton, WhiteButton } from '@silent-voice/web-ui/Button'
import { HeroArtwork } from './HeroArtwork'
import { ImpactBand } from './ImpactBand'
import { siteLinks } from '../site-links'
import { useEntrance } from '../entrance'
import './hero.css'

export function Hero() {
  const enter = useEntrance()

  return (
    <>
      <section id="inicio" className="hero overflow-hidden" aria-labelledby="hero-heading">
        <div className="page-container hero__layout flex items-start justify-between">
          <div className="hero__copy flex shrink-0 flex-col items-start gap-[18px]" data-node-id="10:95">
            <m.p className="hero__eyebrow flex items-center gap-3" data-node-id="10:92" {...enter('eyebrow')}>
              <img src="/assets/user-sound.svg" alt="" />
              <span>Revolução da Fala Assistiva</span>
            </m.p>
            <m.h1 id="hero-heading" className="hero__heading" data-node-id="10:97" {...enter('heading')}>
              A inteligência biomédica<br />{' '}
              que <span className="font-semibold text-accent">transforma intenções<br />{' '}em fala</span> em tempo real.
            </m.h1>
            <m.p className="hero__description" data-node-id="10:98" {...enter('description')}>
              Combinando EMG, visão computacional e IA de borda, o Silent Voice decodifica micro-sinais musculares em palavras em tempo real, com latência inferior a 300ms.
            </m.p>
            <div className="hero__actions flex items-center gap-[6px]" data-node-id="10:112">
              <m.div className="entrance-control shrink-0" {...enter('primaryCta')}>
                <GreenButton href={siteLinks.saibaMais}>Saiba mais</GreenButton>
              </m.div>
              <m.div className="entrance-control shrink-0" {...enter('secondaryCta')}>
                <WhiteButton href={siteLinks.especialista}>Falar com especialista</WhiteButton>
              </m.div>
            </div>
          </div>
          <HeroArtwork />
        </div>
      </section>
      <ImpactBand />
    </>
  )
}
