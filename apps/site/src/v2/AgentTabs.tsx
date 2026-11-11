import { useRef, type CSSProperties } from 'react'
import { Activity, ScanFace, AudioLines } from 'lucide-react'
import { agents, type AgentId } from './agents'
import { CapabilityIcon } from './CapabilityIcon'
import { AGENT_CYCLE_MS } from './useAgentCarousel'
export const agentIcons = { emg: Activity, vision: ScanFace, audio: AudioLines }
export function AgentTabs({
  value,
  onChange,
  prefix,
  portraits = false,
  progress,
}: {
  value: AgentId
  onChange: (id: AgentId) => void
  prefix: string
  portraits?: boolean
  progress?: { cycle: number; running: boolean }
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])
  return (
    <div
      className={`v2-agent-tabs ${portraits ? 'v2-agent-tabs--portraits' : ''}`}
      data-reveal={portraits ? '2' : undefined}
      role="tablist"
      aria-label={portraits ? 'Conheça os agentes' : 'Explore as capacidades'}
    >
      {agents.map((agent, index) => {
        return (
          <button
            type="button"
            key={agent.id}
            role="tab"
            id={`${prefix}-tab-${agent.id}`}
            aria-controls={`${prefix}-panel`}
            aria-label={
              portraits ? `${agent.name} — ${agent.label}` : agent.label
            }
            style={
              portraits
                ? ({
                    '--agent-color': agent.color,
                    '--agent-tint': agent.tint,
                  } as CSSProperties)
                : undefined
            }
            aria-selected={value === agent.id}
            tabIndex={value === agent.id ? 0 : -1}
            ref={(el) => {
              refs.current[index] = el
            }}
            onClick={() => onChange(agent.id)}
            onKeyDown={(event) => {
              let next: number
              if (event.key === 'ArrowRight' || event.key === 'ArrowDown')
                next = (index + 1) % agents.length
              else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp')
                next = (index + agents.length - 1) % agents.length
              else if (event.key === 'Home') next = 0
              else if (event.key === 'End') next = agents.length - 1
              else return
              event.preventDefault()
              onChange(agents[next]!.id)
              refs.current[next]?.focus()
            }}
          >
            {portraits ? (
              <span className={`v2-avatar v2-avatar--${agent.id}`}>
                <span className="v2-avatar-crop">
                  <img
                    src={agent.portrait}
                    alt=""
                    loading="lazy"
                    width="1254"
                    height="1254"
                  />
                </span>
              </span>
            ) : (
              <span className="v2-cap-control" aria-hidden="true">
                <svg
                  className="v2-cap-ring"
                  width="58"
                  height="58"
                  viewBox="0 0 58 58"
                  fill="none"
                  focusable="false"
                >
                  <circle
                    key={`${progress?.cycle}-${progress?.running}`}
                    className={
                      progress?.running && value === agent.id
                        ? 'v2-cap-ring-progress is-running'
                        : 'v2-cap-ring-progress'
                    }
                    style={{ animationDuration: `${AGENT_CYCLE_MS}ms` }}
                    cx="29"
                    cy="29"
                    r="26"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeDasharray="163.36"
                  />
                </svg>
                <span className="v2-cap-icon">
                  <CapabilityIcon id={agent.id} />
                </span>
              </span>
            )}
            {!portraits && <span>{agent.label}</span>}
            {portraits && (
              <span className="v2-tab-indicator" aria-hidden="true">
                <span
                  key={`${progress?.cycle}-${progress?.running}`}
                  className={`v2-tab-progress${progress?.running && value === agent.id ? ' v2-tab-progress--running' : ''}`}
                />
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
