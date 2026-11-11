import * as m from 'motion/react-m'
import { Typography } from '@silent-voice/web-ui/Typography'
import { useSectionEntrance } from '../entrance'
import { AudienceArtwork } from './AudienceArtwork'
import './audience.css'

const audiences = [
  {
    id: 'total',
    title: 'Perda total da voz',
    description:
      'Para quem já não consegue produzir voz e busca uma nova forma de compartilhar o que quer dizer.',
  },
  {
    id: 'partial',
    title: 'Perda parcial da voz',
    description:
      'Para quem ainda tem voz, mas encontra limites para se fazer ouvir em diferentes momentos do dia.',
  },
  {
    id: 'speech',
    title: 'Dificuldades na fala',
    description:
      'Para quem encontra barreiras para articular palavras e deseja participar das conversas com mais autonomia.',
  },
] as const

export function Audience() {
  const { ref, enter } = useSectionEntrance<HTMLDivElement>()
  return (
    <section className="v2-audience" id="atuacao" aria-labelledby="audience-heading">
      <div ref={ref} className="v2-audience-intro">
        <m.div {...enter(0)}>
          <Typography as="span" variant="label" weight="semibold" className="v2-audience-eyebrow">
            Atuação
          </Typography>
        </m.div>
        <m.div {...enter(.08)}>
          <Typography as="h2" variant="h1" id="audience-heading">
            Pensado para quem tem<br />muito a dizer.
          </Typography>
        </m.div>
        <m.div {...enter(.16)}>
          <Typography as="p" variant="body">
            Para quem perdeu a voz, tem limitações vocais ou dificuldades na fala.
            Uma nova possibilidade para se comunicar.
          </Typography>
        </m.div>
      </div>
      <div className="v2-audience-grid">
        {audiences.map((audience) => <AudienceCard key={audience.id} audience={audience} />)}
      </div>
    </section>
  )
}

function AudienceCard({ audience }: { audience: typeof audiences[number] }) {
  const { ref, enter } = useSectionEntrance<HTMLElement>()
  return (
    <article ref={ref} className="v2-audience-card" aria-labelledby={`audience-${audience.id}`}>
      <m.div className="v2-audience-art" {...enter(0, 12, .8)}>
        <AudienceArtwork kind={audience.id} />
      </m.div>
      <m.div className="v2-audience-copy" {...enter(.12, 10)}>
        <Typography as="h3" variant="h3" id={`audience-${audience.id}`}>{audience.title}</Typography>
        <Typography as="p" variant="body">{audience.description}</Typography>
      </m.div>
    </article>
  )
}
