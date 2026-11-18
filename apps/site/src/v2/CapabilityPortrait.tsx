import type { CSSProperties } from 'react'
import { agents, type AgentId } from './agents'
import './capability-portrait.css'

// The overlay uses the raster's coordinate system and the same bottom-centered
// contain fit, so every wave remains attached to the neckband at every breakpoint.
function AudioWaves({ running, reducedMotion }: { running: boolean; reducedMotion: boolean }) {
  return (
    <svg
      className="v2-audio-waves"
      viewBox="0 0 1024 979"
      preserveAspectRatio="xMidYMax meet"
      fill="none"
      aria-hidden="true"
      focusable="false"
      data-reduced-motion={reducedMotion}
      style={{ '--audio-play-state': running ? 'running' : 'paused' } as CSSProperties}
    >
      {[0, 1, 2].map(index => (
        <g
          className="v2-audio-ring"
          key={index}
          style={{ '--wave-delay': `${index * .8}s`, '--rest-scale': 1.8 + index * 2.1 } as CSSProperties}
        >
          <circle className="v2-audio-ring-halo" cx="466" cy="675" r="45" />
          <circle className="v2-audio-ring-line" cx="466" cy="675" r="45" />
        </g>
      ))}
      <circle className="v2-audio-core" cx="466" cy="675" r="33" />
    </svg>
  )
}

export function CapabilityPortrait({ selected, running, reducedMotion }: {
  selected: AgentId
  running: boolean
  reducedMotion: boolean
}) {
  return (
    <div className="v2-cap-portrait" aria-hidden="true">
      {agents.map(agent => (
        <div
          key={agent.id}
          className={`v2-cap-portrait-layer v2-cap-portrait-layer--${agent.id}${agent.id === selected ? ' is-active' : ''}`}
        >
          <img
            src={agent.bentoPortrait}
            alt=""
            width="1024"
            height={agent.bentoPortraitHeight}
            loading="lazy"
            decoding="async"
          />
          {agent.id === 'audio' && <AudioWaves running={running && selected === 'audio'} reducedMotion={reducedMotion} />}
        </div>
      ))}
    </div>
  )
}
