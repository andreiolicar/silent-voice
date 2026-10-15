import { siteLinks } from '../site-links'
import './brand.css'

type BrandProps = {
  size?: 'default' | 'small'
  href?: string
  'data-node-id'?: string
}

export function Brand({
  size = 'default',
  href = siteLinks.inicio,
  ...props
}: BrandProps) {
  return (
    <a
      className={`brand ${size === 'small' ? 'brand--small' : ''} relative block shrink-0`}
      href={href}
      aria-label="Silent Voice — início"
      {...props}
    >
      <img className="brand__icon absolute" src="/assets/icone.svg" alt="" />
      <img
        className="brand__name absolute"
        src="/assets/silent-voice.svg"
        alt=""
      />
    </a>
  )
}
