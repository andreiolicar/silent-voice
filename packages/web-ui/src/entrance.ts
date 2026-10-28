import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { MotionProps } from 'motion/react'

const reducedMotionQuery = '(prefers-reduced-motion: reduce)'

function subscribeToMotionPreference(onChange: () => void) {
  const preference = window.matchMedia(reducedMotionQuery)
  preference.addEventListener('change', onChange)
  return () => preference.removeEventListener('change', onChange)
}

function getMotionPreference() {
  return window.matchMedia(reducedMotionQuery).matches
}

export function useReducedMotionPreference(): boolean {
  return useSyncExternalStore(subscribeToMotionPreference, getMotionPreference, () => false)
}

/** One entrance per mounted section, with immediate keyboard and reduced-motion access. */
export function useSectionEntrance<T extends HTMLElement = HTMLElement>(forceVisible = false, ready = true) {
  const ref = useRef<T>(null)
  const reducedMotion = useReducedMotionPreference()
  const [entered, setEntered] = useState(false)
  const [focused, setFocused] = useState(false)
  const immediate = reducedMotion || focused || forceVisible
  const visible = (entered && ready) || immediate
  const revealOnFocus = useCallback(() => setFocused(true), [])

  useEffect(() => {
    if (entered) return
    if (immediate) {
      setEntered(true)
      return
    }
    if (!ready) return
    const element = ref.current
    if (!element) return
    const observer = new IntersectionObserver(([entry]) => {
      if (entry?.isIntersecting && entry.intersectionRatio >= 0.2) {
        setEntered(true)
        observer.disconnect()
      }
    }, { threshold: [0, 0.2] })
    observer.observe(element)
    return () => observer.disconnect()
  }, [entered, immediate, ready])

  function enter(delay: number, y = 16, duration = 0.65): MotionProps {
    return {
      initial: immediate ? false : { opacity: 0, y },
      animate: visible ? { opacity: 1, y: 0 } : { opacity: 0, y },
      transition: {
        duration: immediate ? 0 : duration,
        delay: immediate ? 0 : delay,
        ease: [0.2, 0.8, 0.2, 1],
      },
    }
  }

  return { ref, visible, immediate, enter, revealOnFocus }
}
