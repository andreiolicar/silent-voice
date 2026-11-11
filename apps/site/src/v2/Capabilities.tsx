import { Typography } from '@silent-voice/web-ui/Typography'
import { AgentTabs } from './AgentTabs'
import { agentFor } from './agents'
import { useAgentCarousel } from './useAgentCarousel'
import { ProcessArt } from './ProcessArt'
import { CapabilityPortrait } from './CapabilityPortrait'
export function Capabilities() {
  const { ref, selected, cycle, select, running, reducedMotion } = useAgentCarousel()
  const agent = agentFor(selected)
  return (
    <section
      ref={ref}
      className="v2-capabilities"
      id="capacidades"
      aria-labelledby="cap-title"
    >
      <div className="v2-section-intro">
        <span className="v2-eyebrow" data-reveal="0">Capacidades</span>
        <Typography as="h2" variant="h1" id="cap-title" data-reveal="1">
          Perceber. Interpretar.
          <br />
          <span>Dar voz.</span>
        </Typography>
        <Typography as="p" variant="body" data-reveal="2">
          Uma tecnologia que reúne diferentes sinais
          <br className="v2-desktop-break" /> em torno do que você quer
          comunicar.
        </Typography>
      </div>
      <div className="v2-bento">
        <div className="v2-cap-selector" data-reveal="0">
          <span className="v2-bento-label">Capacidades</span>
          <AgentTabs
            value={selected}
            onChange={(id) => {
              if (id !== selected) select(id)
            }}
            prefix="cap"
            progress={{ cycle, running }}
          />
          <Typography as="p" variant="body">
            Explore os sentidos
            <br />
            do Silent Voice.
          </Typography>
        </div>
        <div
          className={`v2-cap-panel v2-cap-panel--${selected}`}
          data-reveal="1"
          role="tabpanel"
          id="cap-panel"
          aria-labelledby={`cap-tab-${selected}`}
          tabIndex={0}
        >
          <CapabilityPortrait selected={selected} running={running} reducedMotion={reducedMotion} />
          <div className="v2-cap-copy">
            <span>{agent.label}</span>
            <Typography as="h3" variant="h3">{agent.capability}</Typography>
            <Typography as="p" variant="body">{agent.capabilityCopy}</Typography>
          </div>
        </div>
        <article className="v2-process-card" data-reveal="0">
          <ProcessArt kind="capture" />
          <span className="v2-step">01 / CAPTAR</span>
          <Typography as="h3" variant="h3">
            Pequenos sinais.
            <br />
            Novas possibilidades.
          </Typography>
          <Typography as="p" variant="body">
            Músculos, movimentos e contexto. Diferentes fontes de informação
            sobre a articulação.
          </Typography>
        </article>
        <article className="v2-process-card" data-reveal="1">
          <ProcessArt kind="fusion" />
          <span className="v2-step">02 / INTERPRETAR</span>
          <Typography as="h3" variant="h3">
            Mais perspectivas.
            <br />
            Um mesmo propósito.
          </Typography>
          <Typography as="p" variant="body">
            Os núcleos se complementam para ajudar no reconhecimento das
            palavras articuladas.
          </Typography>
        </article>
        <article className="v2-process-card" data-reveal="2">
          <ProcessArt kind="voice" />
          <span className="v2-step">03 / COMUNICAR</span>
          <Typography as="h3" variant="h3">
            A sua expressão
            <br />
            ganha voz.
          </Typography>
          <Typography as="p" variant="body">
            O alto-falante do dispositivo reproduz em áudio as palavras
            reconhecidas pelo sistema.
          </Typography>
        </article>
      </div>
    </section>
  )
}
