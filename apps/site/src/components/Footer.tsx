import * as m from 'motion/react-m'
import { useSectionEntrance } from '../entrance'
import { footerAiLinks, footerColumns, footerSocialLinks } from '../footer-content'
import { siteLinks } from '../site-links'
import { Brand } from '@silent-voice/web-ui/Brand'
import { ActionControl } from '@silent-voice/web-ui/ActionControl'
import { SmallGreenButton } from '@silent-voice/web-ui/Button'
import { AiProviderIcon } from './ui/AiProviderIcon'
import { SocialIcon } from './ui/SocialIcon'
import './footer.css'

function ExternalArrow() {
  return (
    <svg className="footer-link__arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d="M4 12 12 4M5 4h7v7" />
    </svg>
  )
}

export function Footer() {
  const { ref: card, enter, revealOnFocus } = useSectionEntrance<HTMLDivElement>()

  return (
    <footer className="site-footer" aria-label="Rodapé do Silent Voice">
      <m.div ref={card} className="page-container site-footer__card entrance-control" onFocusCapture={revealOnFocus} {...enter(0, 12, .6)}>
        <div className="site-footer__top">
          <div className="site-footer__brand">
            <Brand size="small" />
            <p className="site-footer__tagline">Sua intenção ganha voz. Mais autonomia para se comunicar.</p>
          </div>
          <nav className="site-footer__navigation" aria-label="Links do rodapé">
            {footerColumns.map(column => (
              <div className="site-footer__column" key={column.title}>
                <h2>{column.title}</h2>
                <ul>
                  {column.links.map(link => (
                    <li key={link.label}>
                      <ActionControl className="footer-link" href={link.href}>
                        <span className="footer-link__dot" aria-hidden="true" />
                        <span className="footer-link__label">
                          {link.label}
                          {link.external && <ExternalArrow />}
                        </span>
                      </ActionControl>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </div>
        <section className="site-footer__ask" aria-labelledby="footer-ai-heading">
          <h2 id="footer-ai-heading">Ainda com dúvida? Pergunte à IA que você já usa</h2>
          <ul className="site-footer__ai-links">
            {footerAiLinks.map(link => (
              <li key={link.provider}>
                <a className="footer-ai-link" href={link.href} target="_blank" rel="noopener noreferrer" aria-label={`${link.accessibleLabel} (abre em nova aba)`}>
                  <AiProviderIcon provider={link.provider} />
                  <span className="footer-tooltip" aria-hidden="true">{link.label}</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
        <div className="site-footer__row">
          <SmallGreenButton href={siteLinks.contato}>Fale com a equipe</SmallGreenButton>
          <div className="site-footer__socials" role="group" aria-label="Redes sociais do Silent Voice">
            {footerSocialLinks.map(link => (
              <ActionControl className={`footer-social${link.text ? '' : ' footer-social--icon'}`} href={link.href} aria-label={link.label} key={link.platform}>
                <SocialIcon platform={link.platform} />
                {link.text ? <span>{link.text}</span> : <span className="footer-tooltip" aria-hidden="true">{link.platform === 'linkedin' ? 'LinkedIn' : 'YouTube'}</span>}
              </ActionControl>
            ))}
          </div>
        </div>
      </m.div>
      <p className="page-container site-footer__copyright">© {new Date().getFullYear()} Silent Voice. Todos os direitos reservados.</p>
    </footer>
  )
}
