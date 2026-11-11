import { useLayoutEffect, useRef } from 'react'
import { useReducedMotionPreference } from '../entrance'
import { useIntroState } from '../intro/IntroProvider'
import './page-entrance.css'

/** Reveal each marked element once, without remounting its interactive content. */
export function usePageEntrance() {
  const ref = useRef<HTMLDivElement>(null)
  const { ready, immediate } = useIntroState()
  const reducedMotion = useReducedMotionPreference()

  useLayoutEffect(() => {
    const root = ref.current
    if (!root) return
    const elements = [...root.querySelectorAll<HTMLElement>('[data-reveal]')]
    const pending = elements.filter(element => !element.hasAttribute('data-revealed'))
    if (immediate || reducedMotion || !('IntersectionObserver' in window)) {
      elements.forEach(element => {
        element.setAttribute('data-revealed', 'immediate')
        element.removeAttribute('data-reveal-pending')
      })
      return
    }
    pending.forEach(element => element.setAttribute('data-reveal-pending', ''))
    const show = (element: Element, instant = false) => {
      element.removeAttribute('data-reveal-pending')
      element.setAttribute('data-revealed', instant ? 'immediate' : 'animated')
      observer.unobserve(element)
    }
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting && entry.intersectionRatio >= .15) show(entry.target)
      })
    }, { threshold: .15 })
    if (ready) pending.forEach(element => observer.observe(element))

    // Keyboard and anchor navigation must never land on an invisible control.
    const onFocus = (event: FocusEvent) => {
      if (!(event.target instanceof Element)) return
      elements.forEach(element => {
        if (element.contains(event.target as Node) || event.target === element) show(element, true)
      })
    }
    root.addEventListener('focusin', onFocus)
    return () => {
      observer.disconnect()
      root.removeEventListener('focusin', onFocus)
    }
  }, [ready, immediate, reducedMotion])

  return ref
}
