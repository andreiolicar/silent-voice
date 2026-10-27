import type { ReactNode } from 'react'
import type { HTMLMotionProps } from 'motion/react'
import * as m from 'motion/react-m'

type SectionHeadingProps = Omit<HTMLMotionProps<'h2'>, 'children'> & {
  as?: 'h2' | 'h3'
  children: ReactNode
}

export function SectionHeading({ as = 'h2', className = '', children, ...props }: SectionHeadingProps) {
  const Heading = as === 'h3' ? m.h3 : m.h2
  return <Heading {...props} className={`section-heading ${className}`}>{children}</Heading>
}
