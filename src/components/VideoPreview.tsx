import * as m from 'motion/react-m'
import type { HTMLMotionProps } from 'motion/react'
import './video-preview.css'

type VideoPreviewProps = Omit<HTMLMotionProps<'button'>, 'children' | 'type' | 'aria-disabled'> & {
  label: string
  cover: string
}

/** Preview for an upcoming video; the cover and play control move as one unit. */
export function VideoPreview({ label, cover, ...props }: VideoPreviewProps) {
  return (
    <m.button {...props} className="video-preview entrance-control" type="button" aria-disabled="true">
      <span className="video-preview__thumbnail" aria-hidden="true">
        <span className="video-preview__artwork">
          <img className="video-preview__image" src={cover} width="640" height="360"
            alt="" loading="lazy" decoding="async" />
        </span>
        <span className="video-preview__play">
          <svg viewBox="0 0 12 12" focusable="false">
            <path d="M4 2.5 10 6 4 9.5Z" fill="currentColor"
              stroke="currentColor" strokeWidth="1" strokeLinejoin="round" />
          </svg>
        </span>
      </span>
      <span>{label}</span>
    </m.button>
  )
}
