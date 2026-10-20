import { useState } from 'react'
import * as m from 'motion/react-m'
import { useSectionEntrance } from '../entrance'
import { SectionEyebrow } from './SectionEyebrow'
import { SectionHeading } from './SectionHeading'
import { VideoPreview } from './VideoPreview'
import { ExplodedDeviceMedia } from './device-integrated/ExplodedDeviceMedia'
import './communication-section.css'

export function CommunicationSection() {
  const { ref: section, visible, immediate, enter, revealOnFocus } = useSectionEntrance()
  const [mediaEntranceReady, setMediaEntranceReady] = useState(false)

  return (
    <section ref={section} id="comunicacao" className="communication-section" aria-labelledby="communication-heading"
      onFocusCapture={event => {
        if (event.target instanceof HTMLElement && event.target.matches(':focus-visible')) revealOnFocus()
      }}>
      <div className="page-container communication-section__layout">
        <m.div
          className="communication-section__media"
          {...enter(0, 8, .45)}
          onAnimationComplete={() => { if (visible) setMediaEntranceReady(true) }}
        >
          <ExplodedDeviceMedia entranceReady={immediate || mediaEntranceReady} skipEntrance={immediate} />
        </m.div>

        <div className="communication-section__copy">
          <div className="communication-section__details">
            <div className="communication-section__intro">
            <SectionEyebrow {...enter(.1, 10)}>Comunicação assistiva</SectionEyebrow>
            <SectionHeading id="communication-heading" {...enter(.18, 18)}>
              Transforme suas intenções<br />{' '}em fala, em tempo real
            </SectionHeading>
            <m.p className="communication-section__description" {...enter(.28)}>
              O Silent Voice combina EMG, visão computacional e<br />{' '}
              IA de borda para transformar suas intenções em palavras.
            </m.p>
            </div>

            <ul className="communication-section__benefits">
              <m.li {...enter(.4, 12)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
                  <path d="M2 12h20M4 16v4a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-4M10 8V4a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v4M20 16v1a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-1M14 8V7a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1" />
                </svg>
                <p>Comunique-se com mais autonomia no dia a dia.</p>
              </m.li>
              <m.li {...enter(.48, 12)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
                  <path d="M3 3v16a2 2 0 0 0 2 2h16M7 13l3-3 4 4 5-5" />
                </svg>
                <p>Transforme sinais musculares em fala em tempo real.</p>
              </m.li>
            </ul>
          </div>

          <VideoPreview label="Veja o Silent Voice em ação" cover="/assets/silent-voice-demo-cover-wide.webp"
            {...enter(.6, 10, .6)} />
        </div>
      </div>
    </section>
  )
}
