import type { ComponentProps } from 'react'
import './input.css'

export function Input({ className = '', ...props }: ComponentProps<'input'>) {
  return <input {...props} className={`sv-input ${className}`.trim()} />
}
