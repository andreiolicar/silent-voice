import { useEffect, useId, useState } from 'react'
import { useTransform } from 'motion/react'
import type { MotionValue } from 'motion/react'
import type { MotionProps } from 'motion/react'
import * as m from 'motion/react-m'
import { CONVERSATION_DURATION, sampleConversation, samplePhoneRing } from './conversation'
import { useLoopClock, useOnceClock } from './useLoopClock'
import './card-illustration.css'

type EntranceKind = 'rise' | 'line' | 'signature' | 'bar'
type Entrance = (delay: number, kind?: EntranceKind) => MotionProps

type ArtProps = {
  id: string
  enter: Entrance
  running: boolean
  immediate: boolean
  metric: string
}

type CardIllustrationProps = {
  kind: 'communication' | 'care' | 'technology'
  active: boolean
  running: boolean
  immediate: boolean
  metric?: string
}

// Each illustration shares the reference's 396 × 235 coordinate system.
// The generated IDs keep its gradient and mask references local to this instance.
export function CardIllustration({ kind, active, running, immediate, metric = '<300ms' }: CardIllustrationProps) {
  const id = useId().replace(/:/g, '')
  const [started, setStarted] = useState(active || immediate)
  useEffect(() => {
    if (active || immediate) setStarted(true)
  }, [active, immediate])
  const visible = started || immediate

  const enter: Entrance = (delay, kind = 'rise') => {
    const hidden = kind === 'line' ? { scaleX: 0 }
      : kind === 'bar' ? { scaleY: 0 }
      : kind === 'signature' ? { pathLength: 0 }
      : { opacity: 0, y: 10 }
    const shown = kind === 'line' ? { scaleX: 1 }
      : kind === 'bar' ? { scaleY: 1 }
      : kind === 'signature' ? { pathLength: 1 }
      : { opacity: 1, y: 0 }
    const duration = { rise: .62, line: 1.2, bar: .55, signature: 1.15 }[kind]
    return {
      initial: immediate ? false : hidden,
      animate: visible ? shown : hidden,
      transition: {
        delay: immediate ? 0 : delay,
        duration: immediate ? 0 : duration,
        ease: kind === 'signature' ? [.42, 0, .28, 1] : [.22, 1, .36, 1],
      },
    }
  }
  const props = { id, enter, running: running && visible && !immediate, immediate, metric }
  return (
    <div className="card-illustration" aria-hidden="true">
      <svg viewBox="0 0 396 235" fill="none" focusable="false" aria-hidden="true">
        {kind === 'communication' ? <CommunicationArt {...props} /> : kind === 'care' ? <CareArt {...props} /> : <TechnologyArt {...props} />}
      </svg>
    </div>
  )
}

const waveHeights = [8.0, 28.0, 6.0, 38.0, 32.0, 4.0, 6.0, 30.0, 4.0, 4.0, 34.0, 34.0, 26.0, 10.0, 4.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 6.0, 18.0, 30.0, 24.0, 36.0, 12.0, 8.0, 26.0, 34.0, 20.0, 6.0, 3.0, 3.0, 3.0, 3.0, 3.0, 10.0, 30.0, 22.0, 38.0, 16.0, 6.0, 28.0, 12.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0]

type ConversationFrame = ReturnType<typeof sampleConversation>
function useBubbleMotion(frame: MotionValue<ConversationFrame>, side: 'incoming' | 'reply') {
  const opacity = useTransform(frame, value => value[side].opacity)
  const scale = useTransform(frame, value => value[side].scale)
  const y = useTransform(frame, value => value[side].y)
  const first = useTransform(frame, value => value[side].lines[0])
  const second = useTransform(frame, value => value[side].lines[1])
  const third = useTransform(frame, value => value[side].lines[2] ?? 0)
  return { opacity, scale, y, lines: [first, second, third] }
}

function CommunicationArt({ id, enter, running, immediate }: ArtProps) {
  const clock = useLoopClock(8, running)
  const conversationClock = useOnceClock(CONVERSATION_DURATION, running, immediate)
  const frame = useTransform(conversationClock, sampleConversation)
  const phone = useTransform(clock, samplePhoneRing)
  const incomingMotion = useBubbleMotion(frame, 'incoming')
  const replyMotion = useBubbleMotion(frame, 'reply')
  const complete = { opacity: 1, scale: 1, y: 0, lines: [1, 1, 1] }
  const incoming = immediate ? complete : incomingMotion
  const reply = immediate ? complete : replyMotion
  return (
    <>
      <defs>
        <linearGradient id={`${id}-art-reception-panel`} x1="132.891" y1="77" x2="-14.3783" y2="198.4" gradientUnits="userSpaceOnUse">
          <stop stopOpacity="0.33" stopColor="var(--color-brand)" />
          <stop offset="1" stopColor="var(--color-surface)" />
        </linearGradient>
        <linearGradient id={`${id}-art-reception-bubble`} x1="225.469" y1="65.7803" x2="225.469" y2="115.158" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--color-illustration-tint)" />
          <stop offset="1" stopColor="var(--color-surface)" />
        </linearGradient>
        <linearGradient id={`${id}-art-reception-bubble-edge`} x1="282.844" y1="166.12" x2="179.104" y2="63.4573" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--color-surface)" />
          <stop offset="1" stopColor="var(--color-brand)" />
        </linearGradient>
        <linearGradient id={`${id}-art-reception-fade`} x1="189" y1="0" x2="189" y2="76" gradientUnits="userSpaceOnUse">
          <stop stopOpacity="0" stopColor="var(--color-surface)" />
          <stop offset="1" stopColor="var(--color-surface)" />
        </linearGradient>
        <filter id={`${id}-art-reception-shadow`} x="132.1" y="10.1" width="239.8" height="191.8" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
          <feDropShadow dx="0" dy="4" stdDeviation="8.45" floodColor="var(--color-shadow)" floodOpacity="0.03" />
        </filter>
      </defs>
      <rect width="396" height="235" rx="8" fill="var(--color-surface)" />
      <m.g {...enter(0.0, 'rise')}>
        <rect x="41.8906" y="77" width="182" height="189" rx="16.5456" fill="var(--color-surface)" />
        <rect x="40.8565" y="75.9659" width="184.068" height="191.068" rx="17.5798" stroke={`url(#${id}-art-reception-panel)`} strokeOpacity="0.2" strokeWidth="2.06821" />
      </m.g>
      <m.g {...enter(0.16, 'rise')}>
        <rect x="57.3672" y="138.16" width="152" height="48.2275" rx="8" opacity="0.4" fill="var(--color-illustration-panel)" />
      </m.g>
      <m.g {...enter(0.23, 'rise')}>
        <rect x="57.3672" y="194.421" width="152" height="48.2275" rx="8" opacity="0.4" fill="var(--color-illustration-panel)" />
      </m.g>
      <m.g {...enter(0.38, 'rise')}>
        <g filter={`url(#${id}-art-reception-shadow)`}>
          <rect x="150" y="24" width="204" height="156" rx="16.5456" fill="var(--color-surface)" />
          <rect x="149.5" y="23.5" width="205" height="157" rx="17.0456" stroke="var(--color-illustration-panel)" />
        </g>
        <rect x="168.094" y="41.4111" width="67.4843" height="14.371" rx="7.18551" fill="var(--color-illustration-tint)" />
      </m.g>
      <m.g className="card-illustration__incoming" style={{ opacity: incoming.opacity, scale: incoming.scale, y: incoming.y, transformBox: 'view-box', originX: '168.094px', originY: '115.158px' }}>
        <path fill={`url(#${id}-art-reception-bubble)`} d="M168.094 65.7803H270.844C277.471 65.7803 282.844 71.1529 282.844 77.7803V103.158C282.844 109.786 277.471 115.158 270.844 115.158H180.094C173.466 115.158 168.094 109.786 168.094 103.158V65.7803Z" />
        <path stroke={`url(#${id}-art-reception-bubble-edge)`} strokeOpacity="0.4" d="M270.844 66.2803C277.195 66.2803 282.344 71.429 282.344 77.7803V103.158C282.344 109.509 277.195 114.658 270.844 114.658H180.094C173.742 114.658 168.594 109.509 168.594 103.158V66.2803H270.844Z" />
        <m.line style={{ opacity: incoming.lines[0], scaleX: incoming.lines[0], transformBox: 'view-box', originX: '181.906px', originY: '0px' }} x1="181.906" y1="80.4688" x2="260.438" y2="80.4688" strokeOpacity="0.16" strokeWidth="4" strokeLinecap="round" stroke="var(--color-illustration-accent)" />
        <m.line style={{ opacity: incoming.lines[1], scaleX: incoming.lines[1], transformBox: 'view-box', originX: '181.906px', originY: '0px' }} x1="181.906" y1="90.4688" x2="260.438" y2="90.4688" strokeOpacity="0.16" strokeWidth="4" strokeLinecap="round" stroke="var(--color-illustration-accent)" />
        <m.line style={{ opacity: incoming.lines[2], scaleX: incoming.lines[2], transformBox: 'view-box', originX: '181.906px', originY: '0px' }} x1="181.906" y1="100.469" x2="227.359" y2="100.469" strokeOpacity="0.16" strokeWidth="4" strokeLinecap="round" stroke="var(--color-illustration-accent)" />
      </m.g>
      <m.g className="card-illustration__reply" style={{ opacity: reply.opacity, scale: reply.scale, y: reply.y, transformBox: 'view-box', originX: '340.219px', originY: '162.75px' }}>
        <path d="M340.219 127.906H237.469C230.841 127.906 225.469 133.279 225.469 139.906V150.75C225.469 157.377 230.841 162.75 237.469 162.75H328.219C334.846 162.75 340.219 157.377 340.219 150.75V127.906Z" fill="var(--color-surface-subtle)" />
        <m.line style={{ opacity: reply.lines[0], scaleX: reply.lines[0], transformBox: 'view-box', originX: '267.001px', originY: '0px' }} x1="267.001" y1="140.265" x2="326.406" y2="140.265" strokeOpacity="0.7" strokeWidth="4" strokeLinecap="round" stroke="var(--color-illustration-line-light)" />
        <m.line style={{ opacity: reply.lines[1], scaleX: reply.lines[1], transformBox: 'view-box', originX: '262.188px', originY: '0px' }} x1="262.188" y1="152.132" x2="326.406" y2="152.132" strokeOpacity="0.7" strokeWidth="4" strokeLinecap="round" stroke="var(--color-illustration-line-light)" />
      </m.g>
      <rect width="378" height="76" transform="translate(9 159)" fill={`url(#${id}-art-reception-fade)`} />
      <m.g {...enter(0.1, 'rise')}>
        <rect x="57.3672" y="90.8193" width="35" height="35" rx="9" fill="var(--color-illustration-icon-bg)" />
        <m.path className="card-illustration__phone" style={{ rotate: immediate ? 0 : phone, transformBox: 'view-box', originX: '74.98px', originY: '108.05px' }} d="M83.2974 113.325C83.2974 113.625 83.2391 113.933 83.0974 114.233C82.9557 114.533 82.7724 114.817 82.5307 115.083C82.1224 115.533 81.6724 115.858 81.1641 116.067C80.6641 116.275 80.1224 116.383 79.5391 116.383C78.6891 116.383 77.7807 116.183 76.8224 115.775C75.8641 115.367 74.9057 114.817 73.9557 114.125C72.9974 113.425 72.0891 112.65 71.2224 111.792C70.3641 110.925 69.5891 110.017 68.8974 109.067C68.2141 108.117 67.6641 107.167 67.2641 106.225C66.8641 105.275 66.6641 104.367 66.6641 103.5C66.6641 102.933 66.7641 102.392 66.9641 101.892C67.1641 101.383 67.4807 100.917 67.9224 100.5C68.4557 99.9751 69.0391 99.7168 69.6557 99.7168C69.8891 99.7168 70.1224 99.7668 70.3307 99.8668C70.5474 99.9668 70.7391 100.117 70.8891 100.333L73.3474 104.042L71.5307 106.45L76.8057 111.275L78.7891 109.4C78.7891 109.4 79.7391 110.042 79.9474 110.183L82.7057 112.142C82.9224 112.292 83.0724 112.467 83.1641 112.675C83.2474 112.883 83.2974 113.092 83.2974 113.325Z" fill="var(--color-illustration-accent)" />
      </m.g>
    </>
  )
}

function CareArt({ id, enter, running, immediate }: ArtProps) {
  const clock = useLoopClock(12.32, running)
  const waveX = useTransform(clock, [0, 12.32], [0, -336])
  return (
    <>
      <defs>
        <linearGradient id={`${id}-art-doctor-frame`} x1="178.5" y1="23" x2="178.5" y2="108.481" gradientUnits="userSpaceOnUse">
          <stop stopOpacity="0.33" stopColor="var(--color-brand)" />
          <stop offset="1" stopColor="var(--color-surface)" />
        </linearGradient>
        <filter id={`${id}-art-doctor-shadow`} x="214.045" y="38.79" width="177.347" height="165.864" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
          <feDropShadow dx="0" dy="4" stdDeviation="8.45" floodColor="var(--color-shadow)" floodOpacity="0.03" />
        </filter>
        <linearGradient id={`${id}-art-doctor-fade`} x1="189" y1="0" x2="189" y2="76" gradientUnits="userSpaceOnUse">
          <stop stopOpacity="0" stopColor="var(--color-surface)" />
          <stop offset="1" stopColor="var(--color-surface)" />
        </linearGradient>
      </defs>
      <rect width="396" height="235" rx="8" fill="var(--color-surface)" />
      <m.path {...enter(0.0, 'rise')} d="M255.5 22L255.938 22.0059C265.125 22.2384 272.5 29.7578 272.5 39V236H84.5V39C84.5 29.6112 92.1112 22 101.5 22H255.5Z" stroke={`url(#${id}-art-doctor-frame)`} strokeOpacity="0.2" strokeWidth="2" />
      <m.g {...enter(0.16, 'rise')}>
        <rect x="99.5" y="86.3408" width="152" height="48.2275" rx="8" opacity="0.4" fill="var(--color-illustration-panel)" />
      </m.g>
      <m.g {...enter(0.23, 'rise')}>
        <rect x="99.5" y="142.602" width="152" height="48.2275" rx="8" opacity="0.4" fill="var(--color-illustration-panel)" />
      </m.g>
      <m.rect {...enter(0.3, 'rise')} x="102.5" y="205.862" width="152" height="29.1374" rx="8" fill="var(--color-surface-subtle)" />
      <m.g {...enter(0.5, 'rise')}>
        <rect x="29.5" y="131.512" width="155" height="51.2417" rx="25.62085" fill="var(--color-surface)" />
      </m.g>
      <m.g {...enter(0.38, 'rise')}>
        <g filter={`url(#${id}-art-doctor-shadow)`}>
          <rect x="231.945" y="52.6895" width="141.547" height="130.064" rx="16" fill="var(--color-surface)" />
          <rect x="232.445" y="53.1895" width="140.547" height="129.064" rx="15.5" stroke="var(--color-illustration-panel)" />
        </g>
        <rect x="246" y="68.5" width="25" height="24.8703" rx="12.4351" fill="var(--color-surface-subtle)" />
        <rect x="246" y="105.064" width="25" height="24.8703" rx="12.4351" fill="var(--color-surface-subtle)" />
        <rect x="281.875" y="73.75" width="67.4843" height="14.371" rx="7.18551" fill="var(--color-surface-subtle)" />
        <rect x="281.875" y="110.27" width="67.4843" height="14.371" rx="7.18551" fill="var(--color-surface-subtle)" />
      </m.g>
      <m.path {...enter(0.82, 'signature')} opacity="0.5" pathLength="1" strokeWidth="2" d="M259.991 153.619C264.653 149.663 273.029 143.282 269.229 149.4C265.428 155.517 253.93 159.86 248.656 161.266C254.618 159.21 266.364 155.636 265.648 157.783C264.754 160.467 264.591 160.873 265.648 160.792C266.706 160.711 276.628 156.075 277.604 154.367C278.58 152.659 279.231 158.84 281.264 158.759C283.297 158.678 287.039 155.424 289.316 155.506C291.593 155.587 291.268 157.783 292.813 157.783C294.359 157.783 301.922 154.855 307.29 154.855" stroke="var(--color-illustration-line)" />
      <m.g {...enter(0.1, 'rise')}>
        <rect x="99.5" y="39" width="35" height="35" rx="9" fill="var(--color-illustration-icon-bg)" />
        <path d="M122.045 52.017C122.045 54.8024 119.787 57.0604 117.001 57.0604C114.216 57.0604 111.958 54.8024 111.958 52.017C111.958 49.2316 114.216 46.9736 117.001 46.9736C119.787 46.9736 122.045 49.2316 122.045 52.017Z" fill="var(--color-illustration-accent)" />
        <path d="M124.847 66.0264C124.847 63.9457 124.02 61.9502 122.549 60.4789C121.078 59.0077 119.082 58.1811 117.001 58.1811C114.921 58.1811 112.925 59.0077 111.454 60.4789C109.983 61.9502 109.156 63.9457 109.156 66.0264L124.847 66.0264Z" fill="var(--color-illustration-accent)" />
      </m.g>
      <rect width="378" height="76" transform="translate(9 159.099)" fill={`url(#${id}-art-doctor-fade)`} />
      <m.g {...enter(.5)}>
        <svg x="43.5" y="131.512" width="127" height="51.242" viewBox="0 0 127 51.2417" overflow="hidden">
          <defs>
            <linearGradient id={`${id}-wave-mask-gradient`} x1="0" y1="0" x2="127" y2="0" gradientUnits="userSpaceOnUse">
              <stop stopColor="var(--color-mask)" stopOpacity="0" />
              <stop offset=".18" stopColor="var(--color-mask)" />
              <stop offset=".76" stopColor="var(--color-mask)" />
              <stop offset="1" stopColor="var(--color-mask)" stopOpacity="0" />
            </linearGradient>
            <mask id={`${id}-wave-mask`} x="0" y="0" width="127" height="51.242" maskUnits="userSpaceOnUse">
              <rect width="127" height="51.242" fill={`url(#${id}-wave-mask-gradient)`} />
            </mask>
          </defs>
          <g mask={`url(#${id}-wave-mask)`}>
            <m.g className="card-illustration__wave" style={{ x: immediate ? 0 : waveX }}>
              {[...waveHeights, ...waveHeights].map((height, index) => (
                <rect key={index} x={1.5 + index * 6} y={25.621 - height / 2} width="3" height={height} rx="1.5" fill={height === 3 ? 'var(--color-illustration-line)' : 'var(--color-brand)'} fillOpacity={height === 3 ? 1 : .8} />
              ))}
            </m.g>
          </g>
        </svg>
      </m.g>
    </>
  )
}

function TechnologyArt({ id, enter, metric }: ArtProps) {
  return (
    <>
      <defs>
        <linearGradient id={`${id}-art-manager-panel`} x1="267.372" y1="85.666" x2="169.513" y2="201.978" gradientUnits="userSpaceOnUse">
          <stop stopOpacity="0.33" stopColor="var(--color-brand)" />
          <stop offset="1" stopColor="var(--color-surface)" />
        </linearGradient>
        <linearGradient id={`${id}-art-manager-area`} x1="137.332" y1="102.751" x2="141.57" y2="128.762" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--color-brand)" />
          <stop offset="1" stopOpacity="0.2" stopColor="var(--color-surface)" />
        </linearGradient>
        <linearGradient id={`${id}-art-manager-line`} x1="126.307" y1="108.233" x2="57.0815" y2="132.804" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--color-brand)" />
          <stop offset="1" stopColor="var(--color-surface)" />
        </linearGradient>
        <filter id={`${id}-art-manager-shadow`} x="23.86" y="6.1" width="239.52" height="158.86" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
          <feDropShadow dx="0" dy="4" stdDeviation="8.45" floodColor="var(--color-shadow)" floodOpacity="0.03" />
        </filter>
        <linearGradient id={`${id}-art-manager-fade`} x1="189" y1="0" x2="189" y2="76" gradientUnits="userSpaceOnUse">
          <stop stopOpacity="0" stopColor="var(--color-surface)" />
          <stop offset="1" stopColor="var(--color-surface)" />
        </linearGradient>
      </defs>
      <rect width="396" height="235" rx="8" fill="var(--color-surface)" />
      <m.g {...enter(0.22, 'rise')}>
        <rect x="180.508" y="85.666" width="173.729" height="125.126" rx="16.5456" fill="var(--color-surface)" />
        <rect x="179.474" y="84.6319" width="175.798" height="127.195" rx="17.5798" stroke={`url(#${id}-art-manager-panel)`} strokeOpacity="0.2" strokeWidth="2.06821" />
      </m.g>
      <m.g {...enter(0.0, 'rise')}>
        <g filter={`url(#${id}-art-manager-shadow)`}>
          <rect x="41.7578" y="20" width="203.718" height="123.058" rx="16.5456" fill="var(--color-surface)" />
          <rect x="42.2578" y="20.5" width="202.718" height="122.058" rx="16.0456" stroke="var(--color-illustration-panel)" />
        </g>
        <m.g className="card-illustration__line-chart" style={{ transformBox: 'view-box', originX: '54px', originY: '129px' }} {...enter(.45, 'line')}>
        <path fill={`url(#${id}-art-manager-area)`} fillOpacity="0.2" d="M97.1595 119.734L54.3984 128.986H232.82V77.0732L185.51 100.707L155.398 107.69L123.45 119.734H97.1595Z" />
        <path fill={`url(#${id}-art-manager-line)`} fillOpacity="0.4" d="M54.261 127.754C53.8877 127.83 53.6466 128.194 53.7225 128.567C53.7984 128.94 54.1626 129.181 54.5359 129.106L54.3984 128.43L54.261 127.754ZM155.398 107.69L155.242 107.018L155.197 107.028L155.154 107.044L155.398 107.69ZM184.715 100.891L184.56 100.219L184.715 100.891ZM186.24 100.343L185.932 99.7254L186.24 100.343ZM124.626 119.291L124.382 118.645L124.626 119.291ZM96.4792 119.872L96.6167 120.548L96.4792 119.872ZM54.3984 128.43L54.5359 129.106L96.6167 120.548L96.4792 119.872L96.3418 119.196L54.261 127.754L54.3984 128.43ZM97.8538 119.734V120.424H122.193V119.734V119.044H97.8538V119.734ZM124.626 119.291L124.869 119.936L155.641 108.335L155.398 107.69L155.154 107.044L124.382 118.645L124.626 119.291ZM155.398 107.69L155.554 108.362L184.871 101.563L184.715 100.891L184.56 100.219L155.242 107.018L155.398 107.69ZM186.24 100.343L186.548 100.96L233.129 77.6903L232.82 77.0732L232.512 76.4562L185.932 99.7254L186.24 100.343ZM184.715 100.891L184.871 101.563C185.452 101.429 186.015 101.226 186.548 100.96L186.24 100.343L185.932 99.7254C185.495 99.9434 185.035 100.109 184.56 100.219L184.715 100.891ZM122.193 119.734V120.424C123.107 120.424 124.014 120.258 124.869 119.936L124.626 119.291L124.382 118.645C123.682 118.909 122.941 119.044 122.193 119.044V119.734ZM96.4792 119.872L96.6167 120.548C97.0238 120.465 97.4383 120.424 97.8538 120.424V119.734V119.044C97.346 119.044 96.8394 119.095 96.3418 119.196L96.4792 119.872Z" />
        </m.g>
      </m.g>
      <m.rect {...enter(0.16, 'rise')} x="58.7109" y="37.1406" width="69.7857" height="14.8611" rx="7.43056" fill="var(--color-illustration-tint)" />
      <rect width="378" height="76" transform="translate(0.328125 159)" fill={`url(#${id}-art-manager-fade)`} />
      <m.rect className="card-illustration__bar" x="200.938" y="169.372" width="9.958" height="23.7366" rx="4.13641" fill="var(--color-illustration-tint)" style={{ transformBox: 'view-box', originX: '205.917px', originY: '193.108px' }} {...enter(0.45, 'bar')} />
      <m.rect className="card-illustration__bar" x="218.5" y="156.762" width="9.958" height="36.3464" rx="4.13641" fill="var(--color-illustration-tint)" style={{ transformBox: 'view-box', originX: '223.479px', originY: '193.108px' }} {...enter(0.57, 'bar')} />
      <m.rect className="card-illustration__bar" x="236.062" y="143.745" width="9.958" height="49.3621" rx="4.13641" fill="var(--color-illustration-tint)" style={{ transformBox: 'view-box', originX: '241.04100000000003px', originY: '193.108px' }} {...enter(0.69, 'bar')} />
      <m.rect className="card-illustration__bar" x="253.633" y="165.402" width="9.958" height="27.7055" rx="4.13641" fill="var(--color-illustration-tint)" style={{ transformBox: 'view-box', originX: '258.612px', originY: '193.108px' }} {...enter(0.81, 'bar')} />
      <m.rect className="card-illustration__bar" x="271.188" y="139.271" width="9.958" height="53.8362" rx="4.13641" fill="var(--color-illustration-tint)" style={{ transformBox: 'view-box', originX: '276.167px', originY: '193.108px' }} {...enter(0.93, 'bar')} />
      <m.rect className="card-illustration__bar" x="288.742" y="165.402" width="9.958" height="27.7055" rx="4.13641" fill="var(--color-illustration-tint)" style={{ transformBox: 'view-box', originX: '293.721px', originY: '193.108px' }} {...enter(1.05, 'bar')} />
      <m.rect className="card-illustration__bar" x="306.297" y="126.539" width="9.958" height="66.5686" rx="4.13641" fill="var(--color-illustration-tint)" style={{ transformBox: 'view-box', originX: '311.276px', originY: '193.108px' }} {...enter(1.17, 'bar')} />
      <m.rect className="card-illustration__bar" x="323.852" y="113.471" width="9.958" height="79.6375" rx="4.13641" fill="var(--color-illustration-tint)" style={{ transformBox: 'view-box', originX: '328.83099999999996px', originY: '193.108px' }} {...enter(1.29, 'bar')} />
      <m.g {...enter(.34)}><text className="card-illustration__metric" x="60.0778" y="89.5391">{metric}</text></m.g>
    </>
  )
}
