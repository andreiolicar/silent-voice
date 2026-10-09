import * as m from 'motion/react-m'
import { SmallWhiteButton } from './ui/Button'
import { HeaderNavigation } from './HeaderNavigation'
import { Brand } from './Brand'
import { siteLinks } from '../site-links'
import { useEntrance } from '../entrance'
import './header.css'

export function Header() {
  const enter = useEntrance()

  return (
    <header className="site-header" data-node-id="2:2">
      <m.div className="page-container header-content entrance-control" {...enter('header')}>
        <Brand data-node-id="2:61" />
        <HeaderNavigation />
        <SmallWhiteButton href={siteLinks.participe}>Participe</SmallWhiteButton>
      </m.div>
    </header>
  )
}
