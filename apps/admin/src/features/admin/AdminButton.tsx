import type { ComponentPropsWithRef } from 'react'
import '@silent-voice/web-ui/button.css'
import './admin-button.css'

type AdminButtonVariant = 'primary' | 'secondary'

export type AdminButtonProps = ComponentPropsWithRef<'button'> & {
  variant?: AdminButtonVariant
}

export function adminButtonClassName(
  variant: AdminButtonVariant = 'secondary',
  className = ''
) {
  return `sv-button sv-button--white sv-button--small crm-button crm-button--${variant} ${className}`.trim()
}

export function AdminButton({
  variant = 'secondary',
  className = '',
  type = 'button',
  ...props
}: AdminButtonProps) {
  return (
    <button
      {...props}
      type={type}
      className={adminButtonClassName(variant, className)}
    />
  )
}
