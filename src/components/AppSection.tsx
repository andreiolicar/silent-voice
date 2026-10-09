import { useId } from 'react'
import * as m from 'motion/react-m'
import { useSectionEntrance } from '../entrance'
import { SectionEyebrow } from './SectionEyebrow'
import { SectionHeading } from './SectionHeading'
import { ShowcaseBackdrop } from './ShowcaseBackdrop'
import { VideoPreview } from './VideoPreview'
import './communication-section.css'
import './app-section.css'

function AppPhone() {
  const screenMaskId = useId()

  return (
    <svg className="app-showcase__phone" viewBox="0 0 1024 1200" role="img"
      aria-label="Mão segurando um celular com o aplicativo Silent Voice e o neckband pronto para conectar.">
      <defs>
        <mask id={screenMaskId} maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1536">
          <rect x="310" y="106" width="435" height="954" rx="65" fill="white" />
          <rect x="453" y="118" width="147" height="40" rx="20" fill="black" />
        </mask>
      </defs>
      <image href="/assets/app/hand-phone.webp" width="1024" height="1536" />
      {/* Keep the supplied UI pixels intact; the mask retains the phone's camera island. */}
      <image href="/assets/app/connection-screen.png" x="310" y="106" width="435" height="954"
        preserveAspectRatio="none" mask={`url(#${screenMaskId})`} />
    </svg>
  )
}

export function AppSection() {
  const { ref, enter, revealOnFocus } = useSectionEntrance()

  return (
    <section ref={ref} id="aplicativo" className="communication-section app-section" aria-labelledby="app-heading"
      onFocusCapture={event => {
        if (event.target instanceof HTMLElement && event.target.matches(':focus-visible')) revealOnFocus()
      }}>
      <div className="page-container communication-section__layout">
        <div className="communication-section__copy">
          <div className="communication-section__details">
            <div className="communication-section__intro">
              <SectionEyebrow {...enter(.1, 10)}>Conectado a você</SectionEyebrow>
              <SectionHeading id="app-heading" {...enter(.18, 18)}>
                Seu celular, um centro<br />de acessibilidade e voz
              </SectionHeading>
              <m.p className="communication-section__description" {...enter(.28)}>
                Conecte o Silent Voice ao seu celular e tenha a comunicação<br />
                ao seu alcance, com mais autonomia em cada conversa.
              </m.p>
            </div>
            <ul className="communication-section__benefits">
              <m.li {...enter(.4, 12)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
                  <path d="M8 5l8 14-4 3V2l4 3L8 19" />
                </svg>
                <p>Conecte seu dispositivo em poucos toques.</p>
              </m.li>
              <m.li {...enter(.48, 12)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
                  <path d="M8 9h8M8 13h5M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5A8.5 8.5 0 0 1 10.5 3h2A8.5 8.5 0 0 1 21 11.5Z" />
                </svg>
                <p>Leve sua voz e suas conexões para onde você for.</p>
              </m.li>
            </ul>
          </div>
          <VideoPreview label="Veja como baixar e configurar o app" cover="/assets/app/tutorial-cover-wide.webp"
            {...enter(.6, 10, .6)} />
        </div>

        <m.figure className="app-showcase" {...enter(0, 8, .45)}>
          <ShowcaseBackdrop />
          <m.div className="app-showcase__product" {...enter(.45, 120, 1.05)}>
            <AppPhone />
          </m.div>
        </m.figure>
      </div>
    </section>
  )
}
