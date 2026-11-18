import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { Activity, AudioLines, Layers3 } from 'lucide-react'
import { useReducedMotionPreference } from '../entrance'
import './process-art.css'

type ProcessKind = 'capture' | 'fusion' | 'voice'

function useProcessMotion() {
  const ref = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(false)
  const [pageVisible, setPageVisible] = useState(() => !document.hidden)
  const reducedMotion = useReducedMotionPreference()

  useEffect(() => {
    const element = ref.current
    if (!element) return
    const observer = new IntersectionObserver(
      ([entry]) => setInView(Boolean(entry?.isIntersecting)),
      { threshold: 0 },
    )
    observer.observe(element)
    const onVisibility = () => setPageVisible(!document.hidden)
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      observer.disconnect()
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])

  return { ref, running: inView && pageVisible && !reducedMotion }
}

const connectionPath =
  'M254 17V49.5C254 58.34 246.83 65.5 238 65.5H175C166.16 65.5 159 72.66 159 81.5V94'
const connections = [
  { side: 'tr', transform: undefined },
  { side: 'tl', transform: 'translate(317 0) scale(-1 1)' },
  { side: 'bl', transform: 'translate(317 243) rotate(180)' },
  { side: 'br', transform: 'translate(0 243) scale(1 -1)' },
] as const

function CaptureArt() {
  return (
    <>
      <svg className="v2-capture-network" viewBox="0 0 317 243" fill="none">
        {connections.map(({ side, transform }) => (
          <g key={side} transform={transform}>
            <path d={connectionPath} className="v2-capture-wire" />
            <path
              d={connectionPath}
              className={`v2-capture-energy v2-capture-energy--${side}`}
              data-process-motion=""
            />
          </g>
        ))}
      </svg>
      <span className="v2-capture-hub" data-process-motion="">
        <svg className="v2-capture-ring" viewBox="0 0 58 58" fill="none">
          <circle cx="29" cy="29" r="27" className="v2-capture-ring-base" />
          <circle
            cx="29" cy="29" r="27"
            className="v2-capture-ring-fill"
            transform="rotate(-90 29 29)"
            data-process-motion=""
          />
          <circle
            cx="29" cy="29" r="27"
            className="v2-capture-ring-fill"
            transform="translate(58 0) scale(-1 1) rotate(-90 29 29)"
            data-process-motion=""
          />
        </svg>
        <Activity size={24} />
      </span>
    </>
  )
}

const steps = [
  { label: 'Sinais', Icon: Activity },
  { label: 'Interpretar', Icon: Layers3 },
  { label: 'Palavras', Icon: AudioLines },
] as const

function FusionArt() {
  return (
    <div className="v2-fusion-track" data-process-motion="">
      {Array.from({ length: 7 }, (_, index) => {
        const { label, Icon } = steps[index % steps.length]!
        return (
          <div className="v2-fusion-item" key={index}>
            <span className="v2-fusion-pill"><Icon size={20} />{label}</span>
            {index < 6 && (
              <svg className="v2-fusion-arrow" viewBox="0 0 7 41" fill="none">
                <path d="M3.5 0V37" stroke="currentColor" />
                <path d="M3.5 41 0 35H7Z" fill="currentColor" />
              </svg>
            )}
          </div>
        )
      })}
    </div>
  )
}

function VoiceArt() {
  return (
    <>
      <span className="v2-voice-wave v2-voice-wave--outer" data-process-motion="" />
      <span className="v2-voice-wave v2-voice-wave--inner" data-process-motion="" />
      <span className="v2-voice-core" data-process-motion="">
        <AudioLines className="v2-voice-icon" size={24} data-process-motion="" />
      </span>
    </>
  )
}

export function ProcessArt({ kind }: { kind: ProcessKind }) {
  const { ref, running } = useProcessMotion()
  return (
    <div
      ref={ref}
      className={`v2-process-art v2-process-art--${kind}`}
      style={{ '--process-play-state': running ? 'running' : 'paused' } as CSSProperties}
      aria-hidden="true"
    >
      <div className="v2-process-canvas">
        {kind === 'capture' ? <CaptureArt /> : kind === 'fusion' ? <FusionArt /> : <VoiceArt />}
      </div>
    </div>
  )
}
