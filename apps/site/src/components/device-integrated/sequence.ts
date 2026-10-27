export const RISE_SECONDS = 1.05
export const TOGGLE_SECONDS = 1.6
export const SEQUENCE_EASE = {
  entrance: [.16, 1, .3, 1] as const,
  // Ease the sampled pieces, not the clock: stagger and resume retain their timing.
  expansion: 'linear' as const,
}
const clamp = (value: number) => Math.max(0, Math.min(1, value))
const smooth = (value: number) => { const p = clamp(value); return p * p * (3 - 2 * p) }

/** Independent entrance and reversible pose; covers lead the boards in either direction. */
export function sampleSequence(entrance: number, expansion: number) {
  return {
    groupY: 115 * (1 - clamp(entrance)),
    covers: smooth(expansion / .8),
    components: smooth((expansion - .2) / .8),
    centering: smooth(expansion),
  }
}

/** Attachment coordinates share the cover's progress in either direction. */
export function sampleDeviceGuide(
  guide: { housingAnchor: readonly number[]; lidAnchor: readonly number[] },
  offset: readonly number[],
  covers: number,
) {
  return {
    x1: guide.housingAnchor[0],
    y1: guide.housingAnchor[1],
    x2: guide.lidAnchor[0] + offset[0] * covers,
    y2: guide.lidAnchor[1] + offset[1] * covers,
    opacity: smooth((covers - .1) / .3),
  }
}

export type Channel = 'entrance' | 'expansion'
type Animation = {
  from: number
  to: number
  duration: number
  onComplete: () => void
}
type Options = {
  reduced: boolean
  read: (channel: Channel) => number
  write: (channel: Channel, value: number) => void
  start: (channel: Channel, animation: Animation) => { stop: () => void }
  change?: () => void
}
type Phase = 'loading' | 'entering' | 'closed' | 'opening' | 'open' | 'closing' | 'error'

/** Owns admission and intent, leaving frame updates to MotionValues. */
export function createSequenceSession(options: Options) {
  let mounted = false
  let ready = false
  let entranceReady = false
  let entered = options.reduced
  let reduced = options.reduced
  let visible = true
  let ratio = 0
  let expanded = false
  let error = false
  const values = { entrance: entered ? 1 : 0, expansion: 0 }
  const generations = { entrance: 0, expansion: 0 }
  const controllers: Partial<Record<Channel, { stop: () => void }>> = {}
  const running = () => Boolean(controllers.entrance || controllers.expansion)
  const emit = () => options.change?.()

  function write(channel: Channel, value: number) {
    values[channel] = value
    options.write(channel, value)
  }

  function stop(channel: Channel) {
    const controller = controllers[channel]
    if (!controller) return
    const saved = clamp(options.read(channel))
    delete controllers[channel]
    generations[channel]++
    controller.stop()
    write(channel, saved)
  }

  function start(channel: Channel, to: number, fullDuration: number) {
    if (controllers[channel] || values[channel] === to) return
    const generation = ++generations[channel]
    const from = values[channel]
    controllers[channel] = options.start(channel, {
      from, to, duration: fullDuration * Math.abs(to - from),
      onComplete() {
        if (!mounted || generation !== generations[channel]) return
        delete controllers[channel]
        write(channel, to)
        if (channel === 'entrance') entered = true
        reconcile()
      },
    })
  }

  function reconcile(continuing = false) {
    if (!mounted) return
    const inView = ratio >= .35 || ((running() || continuing) && ratio >= .2)
    const allowed = ready && entranceReady && visible && inView && !error
    if (!allowed) {
      stop('entrance')
      stop('expansion')
    } else if (!entered) {
      start('entrance', 1, RISE_SECONDS)
    } else if (!reduced) {
      start('expansion', expanded ? 1 : 0, TOGGLE_SECONDS)
    }
    emit()
  }

  return {
    mount() {
      mounted = true
      write('entrance', values.entrance)
      write('expansion', values.expansion)
      reconcile()
    },
    unmount() {
      stop('entrance')
      stop('expansion')
      mounted = false
      generations.entrance++
      generations.expansion++
    },
    decoded() {
      if (!mounted || error) return
      ready = true
      reconcile()
    },
    fail() {
      if (!mounted || error) return
      stop('entrance')
      stop('expansion')
      error = true
      expanded = false
      entered = true
      write('entrance', 1)
      write('expansion', 0)
      emit()
    },
    setEntrance(value: boolean) { entranceReady = value; reconcile() },
    setVisible(value: boolean) { visible = value; reconcile() },
    setIntersection(value: number) { ratio = value; reconcile() },
    toggleExpanded() {
      if (!mounted || !ready || !entered || error) return
      const continuing = running()
      stop('expansion')
      expanded = !expanded
      if (reduced) write('expansion', expanded ? 1 : 0)
      reconcile(continuing)
    },
    skipEntrance() {
      if (!mounted || entered || error) return
      stop('entrance')
      entered = true
      write('entrance', 1)
      reconcile()
    },
    setReduced(value: boolean) {
      if (!mounted || error) return
      reduced = value
      if (value) {
        stop('entrance')
        stop('expansion')
        entered = true
        write('entrance', 1)
        write('expansion', expanded ? 1 : 0)
      }
      reconcile()
    },
    snapshot() {
      const phase: Phase = error ? 'error' : !ready ? 'loading' : !entered ? 'entering'
        : values.expansion === (expanded ? 1 : 0) ? (expanded ? 'open' : 'closed')
        : expanded ? 'opening' : 'closing'
      return { phase, expanded, canInteract: ready && entered && !error, running: running(), error }
    },
  }
}
