import { useEffect, useId, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { agents, agentSignalLabels, type AgentId } from './agents'
import { notifyHeroReady } from '../intro/IntroProvider'
import { AgentPill } from './AgentPill'

const signals = [
  { title: agentSignalLabels.vision, path: 'M178 194 H240 Q255 194 270 209 L354 262', x: 354, y: 262 },
  { title: agentSignalLabels.emg, path: 'M515 343 H495 Q480 343 475 328 L420 232', x: 420, y: 232 },
  { title: agentSignalLabels.audio, path: 'M178 467 H220 Q235 467 245 452 L270 414', x: 270, y: 414 },
]

export function HumanHeroScene({ ready, immediate, onSelectAgent }: { ready: boolean; immediate: boolean; onSelectAgent?: (id: AgentId) => void }) {
  const [failed, setFailed] = useState(false)
  const portrait = useRef<HTMLImageElement>(null)
  const connectionId = useId()
  useEffect(() => {
    // A cached image can finish before React attaches its load listener.
    if (portrait.current?.complete && portrait.current.naturalWidth > 0) notifyHeroReady()
  }, [])
  return (
    <div className="v2-human-scene" data-ready={ready} data-immediate={immediate} data-fallback={failed}>
      <div className="v2-human-stage">
        <div className="v2-human-aura" data-hero-enter="aura" aria-hidden="true" />
        {failed ? (
          <img className="v2-human-fallback" data-hero-enter="portrait" src="/assets/device-interactive/closed.webp"
            alt="Dispositivo Silent Voice fechado." width="1296" height="880" />
        ) : (
          <img ref={portrait} className="v2-human-portrait" data-hero-enter="portrait" src="/assets/v2/person-hero-fresh-expanded.png"
            alt="Pessoa usando a neckband Silent Voice com três eletrodos EMG em cada lado do rosto e câmera em uma haste branca. Cena ilustrativa."
            width="1122" height="1402" fetchPriority="high" decoding="async"
            onLoad={notifyHeroReady} onError={() => { setFailed(true); notifyHeroReady() }} />
        )}
        <svg className="v2-human-connections" viewBox="0 0 660 600" aria-hidden="true" focusable="false">
          {agents.map((agent, index) => {
            const signal = signals[index]
            const maskId = `${connectionId}-${agent.id}`
            return (
              <g key={agent.id} data-hero-enter={`connection-${agent.id}`} className={`v2-human-connection v2-human-connection--${agent.id}`}
                style={{ '--signal-color': agent.color } as CSSProperties}>
                <defs>
                  <mask id={maskId} maskUnits="userSpaceOnUse" x="0" y="0" width="660" height="600">
                    <path className="v2-connection-reveal" d={signal.path} pathLength="1" />
                  </mask>
                </defs>
                <path className="v2-connection-base" d={signal.path} />
                <path className="v2-connection-lit" d={signal.path} mask={`url(#${maskId})`} />
                <circle className="v2-connection-dot" cx={signal.x} cy={signal.y} r="4" />
              </g>
            )
          })}
        </svg>
      </div>
      <ul className="v2-human-signals" aria-label="Três inteligências interpretam os sinais captados">
        {agents.map((agent, index) => (
          <li key={agent.id}>
            <AgentPill
              agentId={agent.id}
              href="#equipe"
              onClick={() => onSelectAgent?.(agent.id)}
              entrance={`card-${agent.id}`}
              className={`v2-human-signal v2-human-signal--${agent.id}`}
              ariaLabel={`Conhecer ${agent.name}: ${signals[index].title.toLowerCase()}`}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}
