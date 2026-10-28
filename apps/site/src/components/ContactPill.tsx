import { siteLinks } from '../site-links'
import { SectionStar } from './SectionStar'
import { ActionControl } from '@silent-voice/web-ui/ActionControl'
import './contact-pill.css'

export function ContactPill({ className = '' }: { className?: string }) {
  return (
    <ActionControl className={`contact-pill entrance-control ${className}`} href={siteLinks.contato}>
      <SectionStar />
      <span>Fale com a equipe</span>
    </ActionControl>
  )
}
