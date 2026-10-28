import { useRef, useState } from 'react'
import { Menu, X } from 'lucide-react'
import * as m from 'motion/react-m'
import { SmallWhiteButton } from '@silent-voice/web-ui/Button'
import { HeaderNavigation } from './HeaderNavigation'
import { Brand } from '@silent-voice/web-ui/Brand'
import { siteLinks } from '../site-links'
import { useEntrance } from '../entrance'
import './header.css'

export function Header() {
  const enter = useEntrance()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuButton = useRef<HTMLButtonElement>(null)

  return (
    <header className="site-header" data-node-id="2:2"
      onKeyDown={event => { if (event.key === 'Escape' && menuOpen) { setMenuOpen(false); menuButton.current?.focus() } }}>
      <m.div className="page-container header-content entrance-control" {...enter('header')}>
        <Brand data-node-id="2:61" />
        <div className="header-desktop-navigation"><HeaderNavigation /></div>
        <div className="header-desktop-action"><SmallWhiteButton href={siteLinks.participe}>Participe</SmallWhiteButton></div>
        <button ref={menuButton} type="button" className="header-menu-toggle"
          aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'} aria-expanded={menuOpen}
          aria-controls="mobile-navigation" onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
      </m.div>
      {menuOpen && <div id="mobile-navigation" className="header-mobile-panel page-container"
        onClick={event => { if ((event.target as HTMLElement).closest('a')) setMenuOpen(false) }}>
        <HeaderNavigation />
        <SmallWhiteButton href={siteLinks.participe}>Participe</SmallWhiteButton>
      </div>}
    </header>
  )
}
