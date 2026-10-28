import type { ComponentPropsWithRef } from 'react'
import '@silent-voice/web-ui/button.css'
import './chat-controls.css'

type ChatButtonProps = ComponentPropsWithRef<'button'> & {
  tone?: 'green' | 'white' | 'quiet'
  size?: 'regular' | 'compact' | 'icon'
}

/** Native actions share the landing's button finish without pending-link semantics. */
export function ChatButton({
  tone = 'white',
  size = 'compact',
  type = 'button',
  className = '',
  ...props
}: ChatButtonProps) {
  return (
    <button
      {...props}
      type={type}
      className={`sv-button sv-button--${tone === 'green' ? 'green' : 'white'} sv-button--small sv-chat-button sv-chat-button--${tone} sv-chat-button--${size} ${className}`.trim()}
    />
  )
}
