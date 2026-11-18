import { useId } from 'react'
import { PersonGlyph } from '../components/cards/PersonGlyph'

type AudienceKind = 'total' | 'partial' | 'speech'

// Shared visual vocabulary: pale tiles, filled silhouettes and floating white panels.
// Local IDs allow the three illustrations to coexist without SVG reference collisions.
export function AudienceArtwork({ kind }: { kind: AudienceKind }) {
  const id = `audience-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
  return (
    <svg viewBox="0 0 400 280" fill="none" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}-tile`} x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="var(--audience-tint)" />
          <stop offset="1" stopColor="#fff" />
        </linearGradient>
        <radialGradient id={`${id}-grid`}>
          <stop stopColor="#eaeaea" />
          <stop offset="1" stopColor="#fff" />
        </radialGradient>
        <filter id={`${id}-shadow`} x="-30%" y="-30%" width="160%" height="175%" colorInterpolationFilters="sRGB">
          <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#000" floodOpacity=".035" />
        </filter>
        <PersonGlyph id={`${id}-person`} fill="var(--audience-accent)" />
        <path id={`${id}-message`} d="M8 2H24A8 8 0 0 1 32 10V19A8 8 0 0 1 24 27H14C13.3 27 12.6 27.2 12 27.6L6.4 31.2C5.3 31.9 4 31.1 4 29.8V26.9C4 26.3 3.7 25.8 3.2 25.4C1.2 23.9 0 21.6 0 19V10A8 8 0 0 1 8 2Z" />
      </defs>
      {kind === 'total' ? <TotalVoiceArt id={id} />
        : kind === 'partial' ? <PartialVoiceArt id={id} />
          : <SpeechArt id={id} />}
    </svg>
  )
}

function PersonTile({ id, x, y, size = 76 }: { id: string; x: number; y: number; size?: number }) {
  return (
    <g filter={`url(#${id}-shadow)`}>
      <rect x={x - 4} y={y - 4} width={size + 8} height={size + 8} rx="21" fill="#fff" />
      <rect x={x} y={y} width={size} height={size} rx="17" fill={`url(#${id}-tile)`} stroke="var(--audience-edge)" />
      <use href={`#${id}-person`} transform={`translate(${x + size / 2} ${y + size / 2})`} />
    </g>
  )
}

function Wave({ x, y, heights, muted = false }: { x: number; y: number; heights: number[]; muted?: boolean }) {
  return (
    <g fill={muted ? '#e9e9e9' : 'var(--audience-accent)'}>
      {heights.map((height, i) => (
        <rect key={i} x={x + i * 9} y={y - height / 2} width="5" height={height} rx="2.5" />
      ))}
    </g>
  )
}

function TotalVoiceArt({ id }: { id: string }) {
  return (
    <>
      <path d="M38 97H362M38 185H362M153 8V272M247 8V272" stroke={`url(#${id}-grid)`} strokeWidth="1.5" />
      <rect x="165" y="14" width="70" height="70" rx="18" fill={`url(#${id}-tile)`} stroke="var(--audience-edge)" />
      <path d="M191 35H203.5C204.8 35 206 35.5 206.9 36.4L212.6 42.1C213.5 43 214 44.2 214 45.5V60C214 62.2 212.2 64 210 64H191C188.8 64 187 62.2 187 60V39C187 36.8 188.8 35 191 35Z" fill="var(--audience-accent)" opacity=".48" />
      <path d="M205 36V41C205 42.7 206.3 44 208 44H212M193 51H206M193 57H201" stroke="var(--audience-accent)" strokeWidth="2.5" />
      <rect x="65" y="107" width="74" height="74" rx="18" fill={`url(#${id}-tile)`} stroke="var(--audience-edge)" />
      <path d="M93 135H96.8C97.6 135 98.3 134.7 98.9 134.2L105.6 128.6C106.9 127.5 109 128.4 109 130.1V155.9C109 157.6 106.9 158.5 105.6 157.4L98.9 151.8C98.3 151.3 97.6 151 96.8 151H93C91.3 151 90 149.7 90 148V138C90 136.3 91.3 135 93 135Z" fill="var(--audience-accent)" />
      <path d="M115 136C119 140 119 147 115 151" stroke="var(--audience-accent)" strokeWidth="3" strokeLinecap="round" />
      <PersonTile id={id} x={162} y={103} />
      <rect x="261" y="107" width="74" height="74" rx="18" fill={`url(#${id}-tile)`} stroke="var(--audience-edge)" />
      <use href={`#${id}-message`} transform="translate(282 129)" fill="var(--audience-accent)" opacity=".65" />
      <path d="M290 140H306M290 147H301" stroke="var(--audience-accent)" strokeWidth="2.5" />
      <rect x="165" y="198" width="70" height="70" rx="18" fill={`url(#${id}-tile)`} stroke="var(--audience-edge)" />
      <Wave x={180} y={233} heights={[10, 24, 34, 20, 10]} />
      <g filter={`url(#${id}-shadow)`}>
        <circle cx="239" cy="99" r="26" fill="#fff" />
        <circle cx="239" cy="99" r="20" fill="var(--color-brand)" />
        <path d="M230 99L236 105L248 93" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </>
  )
}

function PartialVoiceArt({ id }: { id: string }) {
  return (
    <>
      <rect x="111" y="100" width="219" height="152" rx="23" fill="var(--audience-tint)" />
      <rect x="117" y="106" width="207" height="140" rx="18" fill="#fff" stroke="var(--audience-edge)" />
      <rect x="134" y="121" width="69" height="7" rx="3.5" fill="var(--audience-edge)" />
      <Wave x={151} y={184} heights={[9, 20, 32, 44, 54, 37, 23, 40, 54, 43, 30, 19, 9]} />
      <rect x="144" y="221" width="110" height="5" rx="2.5" fill="#f1f1f1" />
      <g filter={`url(#${id}-shadow)`}>
        <rect x="44" y="45" width="140" height="142" rx="20" fill="#fff" stroke="#efefef" strokeWidth="1.25" />
        <rect x="60" y="62" width="44" height="7" rx="3.5" fill="#f0f0f0" />
        <Wave x={64} y={109} heights={[5, 9, 17, 10, 5, 6, 13, 20, 11, 5]} muted />
        <rect x="60" y="145" width="91" height="6" rx="3" fill="var(--audience-tint)" />
        <rect x="60" y="159" width="59" height="6" rx="3" fill="#f3f3f3" />
      </g>
      <PersonTile id={id} x={264} y={54} size={70} />
      <g filter={`url(#${id}-shadow)`}>
        <circle cx="190" cy="156" r="22" fill="#fff" />
        <path d="M181 156H199M193 150L199 156L193 162" stroke="var(--audience-accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </>
  )
}

function SpeechArt({ id }: { id: string }) {
  return (
    <>
      <path d="M200 91V128C200 139 190 148 179 148H121C110 148 102 156 102 167M200 128C200 139 210 148 221 148H279C290 148 298 156 298 167" stroke="var(--audience-tint)" strokeWidth="2" />
      <rect x="63" y="52" width="56" height="56" rx="17" fill="#fafafa" stroke="#f3f3f3" />
      <rect x="281" y="52" width="56" height="56" rx="17" fill="#fafafa" stroke="#f3f3f3" />
      <rect x="172" y="177" width="56" height="56" rx="17" fill="#fafafa" stroke="#f3f3f3" />
      <use href={`#${id}-message`} transform="translate(186 190) scale(.875)" fill="var(--audience-edge)" />
      <PersonTile id={id} x={162} y={37} />
      <PersonTile id={id} x={64} y={162} />
      <PersonTile id={id} x={260} y={162} />
      <g filter={`url(#${id}-shadow)`}>
        <rect x="217" y="103" width="64" height="35" rx="16" fill="#fff" stroke="#f0f0f0" />
        <circle cx="237" cy="120.5" r="3" fill="var(--audience-accent)" />
        <circle cx="249" cy="120.5" r="3" fill="var(--audience-accent)" />
        <circle cx="261" cy="120.5" r="3" fill="var(--audience-accent)" />
        <rect x="27" y="133" width="69" height="33" rx="16" fill="#fff" stroke="#f0f0f0" />
        <path d="M42 145H79M42 154H67" stroke="var(--audience-accent)" strokeWidth="3" strokeLinecap="round" opacity=".55" />
      </g>
    </>
  )
}
