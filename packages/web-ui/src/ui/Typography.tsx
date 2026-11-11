import type { HTMLAttributes } from 'react'
import './typography.css'

export type TypographyVariant = 'h1' | 'h2' | 'h3' | 'body' | 'label' | 'caption'
export type TypographyProps = HTMLAttributes<HTMLElement> & {
  /** Choose the document outline independently of the visual size. */
  as: 'h1' | 'h2' | 'h3' | 'p' | 'span'
  variant: TypographyVariant
  weight?: 'regular' | 'medium' | 'semibold'
}

export function Typography({ as: Tag, variant, weight, className = '', ...props }: TypographyProps) {
  return (
    <Tag
      {...props}
      className={[
        'sv-typography',
        `sv-typography--${variant}`,
        weight && `sv-typography--${weight}`,
        className,
      ].filter(Boolean).join(' ')}
    />
  )
}
