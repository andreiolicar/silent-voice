import { siteLinks } from '../site-links'
import { ActionControl } from './ui/ActionControl'

const navigation = [
  { key: 'inicio', label: 'Início', width: 52 },
  { key: 'institucional', label: 'Institucional', width: 92 },
  { key: 'servicos', label: 'Serviços', width: 66 },
  { key: 'investimento', label: 'Investimento', width: 97 },
  { key: 'contato', label: 'Contato', width: 60 },
]

export function HeaderNavigation() {
  return (
    <nav aria-label="Navegação principal" className="header-nav" data-node-id="2:60">
      {navigation.map(({ key, label, width }) => {
        const current = key === 'inicio'
        const content = <>{current && <img src="/assets/marker.svg" alt="" />}<span>{label}</span></>
        const className = 'nav-item flex items-center gap-2 whitespace-nowrap'
        return (
          <ActionControl key={key} href={siteLinks[key]} className={className} style={{ width }} aria-current={current ? 'page' : undefined}>
            {content}
          </ActionControl>
        )
      })}
    </nav>
  )
}
