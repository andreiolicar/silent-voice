import { useCallback, useEffect, useRef, useState } from 'react'
import { useReducedMotionPreference } from '../entrance'
import { agents, type AgentId } from './agents'

export const AGENT_CYCLE_MS = 5000

export function useAgentCarousel({
  initialSelected = 'vision',
  readyCycle,
}: { initialSelected?: AgentId; readyCycle?: number } = {}) {
  const ref = useRef<HTMLElement>(null)
  const [state, setState] = useState({
    selected: initialSelected,
    cycle: 0,
  })
  const [inView, setInView] = useState(false)
  const [pageVisible, setPageVisible] = useState(() => !document.hidden)
  const reducedMotion = useReducedMotionPreference()
  const running =
    inView &&
    pageVisible &&
    !reducedMotion &&
    (readyCycle === undefined || readyCycle === state.cycle)

  useEffect(() => {
    const section = ref.current
    if (!section) return
    const observer = new IntersectionObserver(
      ([entry]) => setInView(Boolean(entry?.isIntersecting)),
      { threshold: 0, rootMargin: '50px 0px' },
    )
    observer.observe(section)
    const onVisibility = () => setPageVisible(!document.hidden)
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      observer.disconnect()
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])

  useEffect(() => {
    if (!running) return
    const timer = window.setTimeout(() => {
      setState((previous) => ({
        selected:
          agents[
            (agents.findIndex((agent) => agent.id === previous.selected) + 1) %
              agents.length
          ]!.id,
        cycle: previous.cycle + 1,
      }))
    }, AGENT_CYCLE_MS)
    return () => window.clearTimeout(timer)
  }, [running, state.cycle])

  const select = useCallback((selected: AgentId) => {
    setState((previous) => ({ selected, cycle: previous.cycle + 1 }))
  }, [])

  return { ref, ...state, select, running, reducedMotion }
}
