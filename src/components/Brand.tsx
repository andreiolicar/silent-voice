import { siteLinks } from '../site-links'
import './brand.css'

type BrandProps = {
  size?: 'default' | 'small'
  'data-node-id'?: string
}

export function Brand({ size = 'default', ...props }: BrandProps) {
  return (
    <a className={`brand ${size === 'small' ? 'brand--small' : ''} relative block shrink-0`} href={siteLinks.inicio} aria-label="Silent Voice — início" {...props}>
      <img className="brand__icon absolute" src="/assets/icone.svg" alt="" />
      <img className="brand__name absolute" src="/assets/silent-voice.svg" alt="" />
    </a>
  )
}
