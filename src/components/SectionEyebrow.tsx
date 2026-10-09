import type { HTMLMotionProps } from 'motion/react'
import * as m from 'motion/react-m'
import { SectionStar } from './SectionStar'

type SectionEyebrowProps = Omit<HTMLMotionProps<'p'>, 'children'> & { children: string }

export function SectionEyebrow({ className = '', children, ...props }: SectionEyebrowProps) {
  return (
    <m.p {...props} className={`section-eyebrow ${className}`}>
      <span>{children}</span>
      <SectionStar />
    </m.p>
  )
}
