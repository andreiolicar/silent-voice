import { useEffect, useRef, useState } from 'react'
import { animate, useMotionValue, useTransform } from 'motion/react'
import { createSequenceSession, sampleSequence, SEQUENCE_EASE } from './sequence'
import geometry from './geometry.json'

type Status = ReturnType<ReturnType<typeof createSequenceSession>['snapshot']>

export function useDeviceSequence(entranceReady: boolean, skipEntrance = false) {
  const stage = useRef<HTMLDivElement>(null)
  const entrance = useMotionValue(0)
  const expansion = useMotionValue(0)
  const [load, setLoad] = useState(false)
  const [decoded, setDecoded] = useState(false)
  const [status, setStatus] = useState<Status>({
    phase: 'loading', expanded: false, canInteract: false, running: false, error: false,
  })
  const session = useRef<ReturnType<typeof createSequenceSession> | null>(null)
  const pose = useTransform(() => sampleSequence(entrance.get(), expansion.get()))
  const riseTransform = useTransform(pose, value => `translateY(${value.groupY / 100 * 440}px)`)
  const centerTransform = useTransform(pose, value => {
    const x = geometry.closedTranslate[0] + (geometry.openTranslate[0] - geometry.closedTranslate[0]) * value.centering
    const y = geometry.closedTranslate[1] + (geometry.openTranslate[1] - geometry.closedTranslate[1]) * value.centering
    return `translate(${x}px, ${y}px) scale(${geometry.scale})`
  })

  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    let alive = true
    const clocks = { entrance, expansion }
    const current = createSequenceSession({
      reduced: preference.matches,
      read: channel => clocks[channel].get(),
      write: (channel, value) => clocks[channel].set(value),
      start: (channel, animation) => animate(clocks[channel], animation.to, {
        duration: animation.duration,
        ease: SEQUENCE_EASE[channel],
        onComplete: animation.onComplete,
      }),
      change: () => { if (alive) setStatus(current.snapshot()) },
    })
    session.current = current
    current.mount()
    const visibility = () => current.setVisible(document.visibilityState === 'visible')
    const changePreference = () => current.setReduced(preference.matches)
    visibility()
    document.addEventListener('visibilitychange', visibility)
    preference.addEventListener('change', changePreference)

    const preload = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        setLoad(true)
        preload.disconnect()
      }
    }, { rootMargin: '300px' })
    const viewport = new IntersectionObserver(entries => {
      for (const entry of entries) current.setIntersection(entry.intersectionRatio)
    }, { threshold: [0, .2, .35, 1] })
    if (stage.current) {
      preload.observe(stage.current)
      viewport.observe(stage.current)
    }
    return () => {
      alive = false
      current.unmount()
      session.current = null
      preload.disconnect()
      viewport.disconnect()
      document.removeEventListener('visibilitychange', visibility)
      preference.removeEventListener('change', changePreference)
    }
  }, [entrance, expansion])

  useEffect(() => { session.current?.setEntrance(entranceReady) }, [entranceReady])
  useEffect(() => { if (skipEntrance) session.current?.skipEntrance() }, [skipEntrance])

  useEffect(() => {
    if (!load) return
    let stale = false
    const current = session.current
    const images = geometry.layers.map(layer => {
      const image = new Image()
      image.src = layer.url
      return image
    })
    void Promise.all(images.map(image => image.decode().then(() => {
      if (!image.naturalWidth) throw new Error('Empty device layer')
    }))).then(() => {
      if (stale || session.current !== current) return
      setDecoded(true)
      current?.decoded()
    }, () => {
      if (!stale && session.current === current) current?.fail()
    })
    return () => { stale = true }
  }, [load])

  return {
    stage, status, decoded, pose, riseTransform, centerTransform,
    toggleExpanded: () => session.current?.toggleExpanded(),
    fail: () => session.current?.fail(),
  }
}
