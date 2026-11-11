import { useEffect, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import * as m from 'motion/react-m'
import { SmallWhiteButton } from '@silent-voice/web-ui/Button'
import { HeaderNavigation } from './HeaderNavigation'
import { Brand } from '@silent-voice/web-ui/Brand'
import { siteLinks } from '../site-links'
import { useEntrance } from '../entrance'
import './header.css'

export function Header({
  participateHref = siteLinks.participe,
}: { participateHref?: string } = {}) {
  const enter = useEntrance()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuButton = useRef<HTMLButtonElement>(null)
  const mobileMenu = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return

    const initialScrollY = window.scrollY
    const desktop = window.matchMedia('(min-width: 1024px)')
    const closeOutside = (event: PointerEvent) => {
      if (!mobileMenu.current?.contains(event.target as Node)) setMenuOpen(false)
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setMenuOpen(false)
      menuButton.current?.focus()
    }
    const closeOnScroll = () => {
      if (Math.abs(window.scrollY - initialScrollY) > 8) setMenuOpen(false)
    }
    const closeOnDesktop = () => {
      if (desktop.matches) setMenuOpen(false)
    }

    document.addEventListener('pointerdown', closeOutside)
    document.addEventListener('keydown', closeOnEscape)
    window.addEventListener('scroll', closeOnScroll, { passive: true })
    desktop.addEventListener('change', closeOnDesktop)
    return () => {
      document.removeEventListener('pointerdown', closeOutside)
      document.removeEventListener('keydown', closeOnEscape)
      window.removeEventListener('scroll', closeOnScroll)
      desktop.removeEventListener('change', closeOnDesktop)
    }
  }, [menuOpen])

  return (
    <header
      className="site-header"
      data-node-id="2:2"
    >
      <m.div
        className="page-container header-content entrance-control"
        {...enter('header')}
      >
        <Brand data-node-id="2:61" />
        <div className="header-desktop-navigation">
          <HeaderNavigation />
        </div>
        <div className="header-desktop-action">
          <SmallWhiteButton href={participateHref}>Participe</SmallWhiteButton>
        </div>
        <div
          ref={mobileMenu}
          className="header-mobile-menu"
          data-open={menuOpen || undefined}
          onBlur={(event) => {
            if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) {
              setMenuOpen(false)
            }
          }}
        >
          <button
            ref={menuButton}
            type="button"
            className="header-menu-toggle"
            aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMenuOpen((open) => !open)}
          >
            Menu <ChevronDown className="header-menu-chevron" aria-hidden="true" />
          </button>
          <div
            id="mobile-navigation"
            className="header-mobile-panel"
            aria-hidden={!menuOpen}
            inert={!menuOpen}
            onClick={(event) => {
              if ((event.target as HTMLElement).closest('a')) {
                setMenuOpen(false)
                menuButton.current?.focus()
              }
            }}
          >
            <HeaderNavigation />
            <div className="header-mobile-action">
              <SmallWhiteButton href={participateHref}>Participe</SmallWhiteButton>
            </div>
          </div>
        </div>
      </m.div>
    </header>
  )
}
