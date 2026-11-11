import { useEffect, useRef, useState } from 'react'
import { agents, type AgentId } from './agents'
import { useAgentCarousel } from './useAgentCarousel'

export function useHeroCarousel() {
  const [identity, setIdentity] = useState({
    selected: 'emg' as AgentId,
    cycle: 0,
  })
  const carousel = useAgentCarousel({
    initialSelected: 'emg',
    readyCycle: identity.cycle,
  })
  const { selected, cycle, reducedMotion, select } = carousel
  const switchedAt = useRef(0)

  useEffect(() => {
    switchedAt.current = performance.now()
  }, [cycle])

  useEffect(() => {
    if (identity.cycle === cycle) return
    if (reducedMotion) {
      setIdentity({ selected, cycle })
      return
    }
    const timer = window.setTimeout(() => setIdentity({ selected, cycle }), 350)
    return () => window.clearTimeout(timer)
  }, [selected, cycle, identity.cycle, reducedMotion])

  function selectPerson(id: AgentId) {
    if (id === selected) return
    if (
      !reducedMotion &&
      cycle > 0 &&
      performance.now() - switchedAt.current < 650
    )
      return
    select(id)
  }

  function next() {
    select(
      agents[
        (agents.findIndex((person) => person.id === selected) + 1) %
          agents.length
      ]!.id,
    )
  }

  return {
    ...carousel,
    identity: reducedMotion ? selected : identity.selected,
    leaving: !reducedMotion && identity.cycle !== cycle,
    selectPerson,
    next,
  }
}
