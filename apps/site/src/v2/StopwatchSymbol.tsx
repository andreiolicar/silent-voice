import { useEffect, useId, useRef, useState } from 'react'
import { useReducedMotionPreference } from '../entrance'
import './stopwatch-symbol.css'

export function StopwatchSymbol() {
  const ref = useRef<HTMLSpanElement>(null)
  const [started, setStarted] = useState(false)
  const [visible, setVisible] = useState(() => !document.hidden)
  const reducedMotion = useReducedMotionPreference()
  const gradientId = useId()

  useEffect(() => {
    const element = ref.current
    if (!element || reducedMotion) return
    // Match the reference: enter fully above the bottom 20%, reset only on exit.
    const enter = new IntersectionObserver(([entry]) => {
      if (entry?.isIntersecting && entry.intersectionRatio >= 1) setStarted(true)
    }, { threshold: 1, rootMargin: '0px 0px -20% 0px' })
    const exit = new IntersectionObserver(([entry]) => {
      if (entry && !entry.isIntersecting) setStarted(false)
    })
    enter.observe(element)
    exit.observe(element)
    return () => { enter.disconnect(); exit.disconnect() }
  }, [reducedMotion])

  useEffect(() => {
    const update = () => setVisible(!document.hidden)
    document.addEventListener('visibilitychange', update)
    return () => document.removeEventListener('visibilitychange', update)
  }, [])

  return (
    <span ref={ref} className="v2-stopwatch" aria-hidden="true"
      data-started={started && !reducedMotion} data-visible={visible}>
      <svg className="v2-stopwatch-svg" viewBox="0 0 48 48" fill="none" focusable="false">
        <defs>
          <linearGradient id={gradientId} x1="24" y1="2" x2="24" y2="46" gradientUnits="userSpaceOnUse">
            <stop className="v2-stopwatch-highlight" />
            <stop offset="1" stopColor="var(--color-brand)" />
          </linearGradient>
        </defs>
        <g className="v2-stopwatch-body" fill={`url(#${gradientId})`}>
          <rect x="22" y="7" width="4" height="7" rx="1.5" />
          <g className="v2-stopwatch-crown">
            <rect x="17.5" y="3" width="13" height="5" rx="2.5" />
          </g>
          <rect x="34" y="10" width="8" height="4.5" rx="2.25" transform="rotate(42 38 12.25)" />
          <circle cx="24" cy="28" r="17" />
          <g stroke="#fff" strokeLinecap="round">
            <path d="M12 28h1M35 28h1M24 39v1" strokeWidth="2" opacity=".3" />
            <g className="v2-stopwatch-hand">
              <path d="M24 28V18" strokeWidth="3.4" />
            </g>
          </g>
          <circle cx="24" cy="28" r="2.2" fill="#fff" />
        </g>
      </svg>
    </span>
  )
}
