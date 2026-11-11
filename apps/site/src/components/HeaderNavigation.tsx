import { siteLinks } from '../site-links'
import { ActionControl } from '@silent-voice/web-ui/ActionControl'

const navigation = [
  { label: 'Início', href: siteLinks.inicio },
  { label: 'Atuação', href: siteLinks.atuacao },
  { label: 'Solução', href: siteLinks.solucao },
  { label: 'Assistentes IA', href: siteLinks.assistentes },
  { label: 'FAQ', href: siteLinks.faq },
]

export function HeaderNavigation() {
  return (
    <nav aria-label="Navegação principal" className="header-nav" data-node-id="2:60">
      {navigation.map(({ label, href }) => (
        <ActionControl key={label} href={href} className="nav-item whitespace-nowrap">
          <span>{label}</span>
        </ActionControl>
      ))}
    </nav>
  )
}
