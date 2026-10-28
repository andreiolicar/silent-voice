import type { AriaAttributes, CSSProperties, ReactNode } from 'react'

type ActionControlProps = {
  children: ReactNode
  href?: string
  className?: string
  style?: CSSProperties
  'aria-label'?: AriaAttributes['aria-label']
  'aria-current'?: AriaAttributes['aria-current']
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
}

export function ActionControl({
  children,
  href,
  type = 'button',
  disabled,
  ...props
}: ActionControlProps) {
  return href ? (
    <a {...props} href={href}>
      {children}
    </a>
  ) : (
    <button
      {...props}
      type={type}
      disabled={disabled}
      aria-disabled={disabled || type === 'button' ? true : undefined}
    >
      {children}
    </button>
  )
}
