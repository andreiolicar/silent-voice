import { useEffect, useRef } from 'react'
import { animate, useMotionValue } from 'motion/react'

/** Stop the RAF driver when inactive; a stopped Motion controller cannot be replayed. */
export function useLoopClock(duration: number, running: boolean) {
  return useClock(duration, running, true)
}

/** A finite entrance clock retains its position and never restarts after completion. */
export function useOnceClock(duration: number, running: boolean, immediate: boolean) {
  return useClock(duration, running, false, immediate)
}

function useClock(duration: number, running: boolean, repeat: boolean, immediate = false) {
  const clock = useMotionValue(0)
  const elapsed = useRef(0)

  useEffect(() => {
    if (immediate) {
      elapsed.current = duration
      clock.set(duration)
      return
    }
    if (!running || (!repeat && elapsed.current >= duration)) return
    const controller = animate(clock, [0, duration], {
      duration,
      ease: 'linear',
      repeat: repeat ? Infinity : 0,
      autoplay: false,
      type: 'keyframes',
      onComplete: () => { if (!repeat) elapsed.current = duration },
    })
    controller.time = elapsed.current
    controller.play()
    return () => {
      const time = controller.time
      controller.stop()
      elapsed.current = repeat ? time % duration : Math.min(duration, time)
    }
  }, [clock, duration, running, repeat, immediate])

  return clock
}
