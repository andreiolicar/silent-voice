import * as m from 'motion/react-m'
import { useSectionEntrance } from '../entrance'
import { siteLinks } from '../site-links'
import './contact-card.css'

export function ContactCard({ immediate: forceVisible = false }: { immediate?: boolean }) {
  const { ref, visible, immediate, revealOnFocus, enter } = useSectionEntrance(forceVisible)

  return (
    <m.figure ref={ref} className="contact-card" onFocusCapture={revealOnFocus} {...enter(0)}>
      <div className="contact-card__portrait" aria-hidden="true">
        <span className="contact-card__backdrop" />
        <img src="/assets/faq-contact-person.png" alt="" width="117" height="146" loading="lazy" decoding="async" />
      </div>
      <m.a className="contact-card__message entrance-control" href={siteLinks.contato} style={{ transformOrigin: '0% 0%' }}
        initial={immediate ? false : { opacity: 0, rotate: 60 }} animate={visible ? { opacity: 1, rotate: 0 } : { opacity: 0, rotate: 60 }}
        transition={{ delay: immediate ? 0 : .2, duration: immediate ? 0 : .85, ease: [.16, 1, .3, 1] }}>
        <span className="contact-card__badge" aria-hidden="true"><img src="/assets/icone.svg" alt="" /></span>
        <span>Clique aqui e fale conosco</span>
      </m.a>
    </m.figure>
  )
}
