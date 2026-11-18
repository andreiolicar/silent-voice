import type { CSSProperties } from 'react'
import { agentFor, agents, agentSignalLabels, type AgentId } from './agents'
import './agent-pill.css'

type AgentPillProps = {
  agentId: AgentId
  ariaLabel: string
  href?: string
  onClick?: () => void
  className?: string
  entrance?: string
  crossfadeAvatar?: boolean
}

/** Shared identity; navigation, positioning and carousel timing belong to the caller. */
export function AgentPill({ agentId, ariaLabel, href, onClick, className = '', entrance, crossfadeAvatar = false }: AgentPillProps) {
  const agent = agentFor(agentId)
  const portraits = crossfadeAvatar ? agents : [agent]
  const attributes = {
    className: `v2-agent-pill ${className}`.trim(),
    style: { '--agent-pill-color': agent.color } as CSSProperties,
    'aria-label': ariaLabel,
    'data-hero-enter': entrance,
    onClick,
  }
  const content = <>
    <span className="v2-agent-pill-avatar" aria-hidden="true" data-crossfade={crossfadeAvatar}>
      {portraits.map((person) => (
        <span key={person.id} className="v2-agent-pill-face" data-active={person.id === agentId}>
          <img className="v2-agent-pill-portrait" src={person.portrait} alt="" width="1254" height="1254" />
          <img className="v2-agent-pill-ia" src={`/assets/v2/ia-badge-${person.id === 'vision' ? 'blue' : person.id === 'emg' ? 'green' : 'pink'}.svg`} alt="" width="22" height="14" />
        </span>
      ))}
    </span>
    <span className="v2-agent-pill-copy">
      <strong>{agent.name}</strong>
      <span>{agentSignalLabels[agentId]}</span>
    </span>
  </>

  return href
    ? <a {...attributes} href={href}>{content}</a>
    : <button {...attributes} type="button">{content}</button>
}
