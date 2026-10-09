import type { AriaAttributes, CSSProperties, ReactNode } from 'react'

type ActionControlProps = {
  children: ReactNode
  href?: string
  className?: string
  style?: CSSProperties
  'aria-label'?: AriaAttributes['aria-label']
  'aria-current'?: AriaAttributes['aria-current']
}

export function ActionControl({ children, href, ...props }: ActionControlProps) {
  return href ? (
    <a {...props} href={href}>{children}</a>
  ) : (
    <button {...props} type="button" aria-disabled="true">{children}</button>
  )
}
