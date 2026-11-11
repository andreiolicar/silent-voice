import { Camera, AudioLines, Activity } from 'lucide-react'
import type { AgentId } from './agents'
const bars = [
  12, 24, 18, 36, 27, 48, 33, 60, 42, 28, 52, 70, 38, 58, 80, 50, 65, 32, 55,
  72, 44, 28, 60, 48, 32, 56, 24, 38, 18, 28, 14,
]
export function SignalVisual({
  id,
  dark = false,
}: {
  id: AgentId
  dark?: boolean
}) {
  return (
    <div
      className={`v2-signal v2-signal--${id} ${dark ? 'v2-signal--dark' : ''}`}
      aria-hidden="true"
    >
      {id === 'vision' ? (
        <>
          <div className="v2-face-scan">
            <span />
            <span />
            <span />
            <span />
            <svg viewBox="0 0 240 120" fill="none">
              <path d="M35 65 75 38 120 50 165 38 205 65 165 86 120 76 75 86Z M35 65H205 M75 38 75 86 M165 38V86" />
              <g>
                {[
                  [35, 65],
                  [75, 38],
                  [120, 50],
                  [165, 38],
                  [205, 65],
                  [165, 86],
                  [120, 76],
                  [75, 86],
                ].map(([cx, cy], i) => (
                  <circle key={i} cx={cx} cy={cy} r="3" />
                ))}
              </g>
            </svg>
            <i />
          </div>
          <span className="v2-signal-caption">
            <Camera size={14} /> Leitura da articulação
          </span>
        </>
      ) : id === 'audio' ? (
        <>
          <div className="v2-sound-rings">
            <i />
            <i />
            <i />
          </div>
          <div className="v2-waveform">
            {bars.map((height, i) => (
              <i key={i} style={{ height, animationDelay: `${i * 0.09}s` }} />
            ))}
          </div>
          <span className="v2-signal-caption">
            <AudioLines size={14} /> Contexto da conversa
          </span>
        </>
      ) : (
        <>
          <div className="v2-emg-grid">
            <svg viewBox="0 0 480 140" fill="none">
              <path
                className="v2-emg-shadow"
                d="M0 72H50L61 61 72 82 86 22 100 122 115 52 129 72H170L185 57 198 83 211 8 226 134 241 47 255 72H300L315 60 328 81 341 32 354 111 369 57 382 72H480"
              />
              <path d="M0 72H50L61 61 72 82 86 22 100 122 115 52 129 72H170L185 57 198 83 211 8 226 134 241 47 255 72H300L315 60 328 81 341 32 354 111 369 57 382 72H480" />
            </svg>
          </div>
          <span className="v2-signal-caption">
            <Activity size={14} /> Sinais da articulação
          </span>
        </>
      )}
    </div>
  )
}
