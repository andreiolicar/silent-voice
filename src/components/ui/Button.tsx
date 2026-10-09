import type { ComponentProps } from 'react'
import { ActionControl } from './ActionControl'
import './button.css'

export type ButtonProps = ComponentProps<typeof ActionControl>

type BaseButtonProps = ButtonProps & {
  tone: 'green' | 'white'
  size: 'normal' | 'small'
}

function Button({ tone, size, className = '', ...props }: BaseButtonProps) {
  const classes = `sv-button sv-button--${tone} sv-button--${size} ${className}`.trim()

  return <ActionControl {...props} className={classes} />
}

export function GreenButton(props: ButtonProps) {
  return <Button {...props} tone="green" size="normal" />
}

export function WhiteButton(props: ButtonProps) {
  return <Button {...props} tone="white" size="normal" />
}

export function SmallGreenButton(props: ButtonProps) {
  return <Button {...props} tone="green" size="small" />
}

export function SmallWhiteButton(props: ButtonProps) {
  return <Button {...props} tone="white" size="small" />
}
