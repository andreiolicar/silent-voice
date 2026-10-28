import { useSectionEntrance as useSharedEntrance, useReducedMotionPreference } from '@silent-voice/web-ui/entrance'
export { useReducedMotionPreference }
import type { MotionProps } from 'motion/react'
import { useIntroState } from './intro/IntroProvider'

type EntranceStep = {
  delay: number
  duration: number
  y?: number
  scale?: number
}

// Seconds from mount; overlapping steps keep the entrance continuous.
const sequence = {
  header: { delay: 0.04, duration: 0.55, y: 8 },
  eyebrow: { delay: 0.18, duration: 0.6, y: 12 },
  heading: { delay: 0.26, duration: 0.7, y: 18 },
  description: { delay: 0.38, duration: 0.65, y: 14 },
  primaryCta: { delay: 0.5, duration: 0.6, y: 10 },
  secondaryCta: { delay: 0.58, duration: 0.6, y: 10 },
  backdrop: { delay: 0.24, duration: 0.9, scale: 0.96 },
  portrait: { delay: 0.36, duration: 0.9, y: 20 },
  card: { delay: 0.65, duration: 0.65, y: 12 },
  artworkMenu: { delay: 0.78, duration: 0.6, y: 10 },
  conversation: { delay: 0.9, duration: 0.6, y: 12 },
  upperLine: { delay: 1.06, duration: 0.35 },
  hub: { delay: 1.12, duration: 0.5, scale: 0.9 },
  branches: { delay: 1.26, duration: 0.35 },
  leftNode: { delay: 1.32, duration: 0.5, scale: 0.9 },
  middleNode: { delay: 1.39, duration: 0.5, scale: 0.9 },
  rightNode: { delay: 1.46, duration: 0.5, scale: 0.9 },
} satisfies Record<string, EntranceStep>

type StepName = keyof typeof sequence
type EntranceProps = MotionProps & {
  'data-entrance': StepName
  'data-entrance-transform'?: 'true'
}

export function useSectionEntrance<T extends HTMLElement = HTMLElement>(forceVisible = false) {
  const intro = useIntroState()
  return useSharedEntrance<T>(forceVisible, intro.ready)
}

export function useEntrance(ready = true) {
  const intro = useIntroState()
  const reducedMotion = useReducedMotionPreference()
  const immediate = reducedMotion || intro.immediate

  return (name: StepName): EntranceProps => {
    const step: EntranceStep = sequence[name]
    const hidden = {
      opacity: 0,
      ...(step.y !== undefined ? { y: step.y } : {}),
      ...(step.scale !== undefined ? { scale: step.scale } : {}),
    }
    const visible = {
      opacity: 1,
      ...(step.y !== undefined ? { y: 0 } : {}),
      ...(step.scale !== undefined ? { scale: 1 } : {}),
    }

    return {
      'data-entrance': name,
      'data-entrance-transform': step.y !== undefined || step.scale !== undefined ? 'true' : undefined,
      initial: immediate ? false : hidden,
      animate: (ready && intro.ready) || immediate ? visible : hidden,
      transition: {
        duration: immediate ? 0 : step.duration,
        delay: immediate ? 0 : step.delay,
        ease: [0.2, 0.8, 0.2, 1],
      },
    }
  }
}
