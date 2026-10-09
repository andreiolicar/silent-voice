import { useEffect, useRef, useState } from 'react'
import * as m from 'motion/react-m'
import { useReducedMotionPreference } from '../entrance'
import { CardIllustration } from './cards/CardIllustration'
import { SectionHeading } from './SectionHeading'
import './audience-section.css'
import { useIntroState } from '../intro/IntroProvider'

const cards = [
  {
    kind: 'communication',
    title: 'Para quem usa',
    lead: 'Sua intenção ganha voz.',
    description: 'Transforme sinais em palavras e se comunique com mais autonomia.',
  },
  {
    kind: 'care',
    title: 'Para quem cuida',
    lead: 'Cada conversa aproxima.',
    description: 'Mais possibilidades de cuidado e conexão em cada conversa.',
  },
  {
    kind: 'technology',
    title: 'Para o dia a dia',
    lead: 'Tecnologia que acompanha você.',
    description: 'EMG, visão computacional e IA de borda transformam intenção em fala.',
  },
] as const

export function AudienceSection() {
  const reducedMotion = useReducedMotionPreference()
  const [pageVisible, setPageVisible] = useState(() => !document.hidden)
  useEffect(() => {
    const onVisibility = () => setPageVisible(!document.hidden)
    document.addEventListener('visibilitychange', onVisibility)
    onVisibility()
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [])

  return (
    <section id="para-quem" className="audience-section" aria-label="Silent Voice na comunicação, no cuidado e no dia a dia">
      <div className="page-container audience-section__grid">
        {cards.map((card, index) => (
          <AudienceCard key={card.kind} card={card} index={index} reducedMotion={reducedMotion} pageVisible={pageVisible} />
        ))}
      </div>
    </section>
  )
}

function AudienceCard({ card, index, reducedMotion, pageVisible }: {
  card: typeof cards[number]
  index: number
  reducedMotion: boolean
  pageVisible: boolean
}) {
  const intro = useIntroState()
  const element = useRef<HTMLElement>(null)
  const [entered, setEntered] = useState(reducedMotion)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const cardElement = element.current
    if (!cardElement) return
    const observer = new IntersectionObserver(([entry]) => {
      // isIntersecting alone remains true below the animation's 20% threshold.
      const inView = entry.isIntersecting && entry.intersectionRatio >= .2
      setVisible(inView)
      if (inView && intro.ready) setEntered(true)
    }, { threshold: [0, .2] })
    observer.observe(cardElement)
    return () => observer.disconnect()
  }, [intro.ready])
  useEffect(() => {
    if (reducedMotion) setEntered(true)
  }, [reducedMotion])
  const active = (entered && intro.ready) || reducedMotion
  return (
    <article ref={element} className="audience-card" data-card={card.kind}>
      <CardIllustration kind={card.kind} active={active} running={intro.ready && visible && pageVisible && !reducedMotion} immediate={reducedMotion} />
      <m.div className="audience-card__copy"
        initial={reducedMotion ? false : { opacity: 0, y: 12 }}
        animate={active ? { opacity: 1, y: 0 } : { opacity: 0, y: 12 }}
        transition={{ delay: reducedMotion ? 0 : .18 + index * .08, duration: reducedMotion ? 0 : .6, ease: [.2, .8, .2, 1] }}>
        <SectionHeading as="h3">{card.title}</SectionHeading>
        <p><span>{card.lead}</span><br />{card.description}</p>
      </m.div>
    </article>
  )
}
