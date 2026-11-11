import type { SVGProps } from 'react'

/** Shared filled silhouette: rounded shoulders and a head half the body's width. */
export function PersonGlyph(props: SVGProps<SVGGElement>) {
  return (
    <g fill="currentColor" {...props}>
      <circle cx="0" cy="-11" r="10" />
      <path d="M-16.7 23H16.7C18.6 23 20.1 21.4 19.8 19.5C18.2 9.4 10.2 2 0 2S-18.2 9.4-19.8 19.5C-20.1 21.4-18.6 23-16.7 23Z" />
    </g>
  )
}
