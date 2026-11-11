import { useRef, useState } from 'react'
import { ArrowUpRight, Menu, X } from 'lucide-react'
import { Brand } from '@silent-voice/web-ui/Brand'
export function LandingHeader() {
  const [open, setOpen] = useState(false)
  const button = useRef<HTMLButtonElement>(null)
  return (
    <header
      className="v2-header"
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          setOpen(false)
          button.current?.focus()
        }
      }}
    >
      <a className="skip-link" href="#conteudo">
        Pular para o conteúdo
      </a>
      <Brand />
      <nav className="v2-desktop-nav" aria-label="Navegação principal">
        <a href="#equipe">Nossa inteligência</a>
        <a href="#capacidades">Como funciona</a>
      </nav>
      <a className="v2-header-cta" href="#lista">
        Faça parte <ArrowUpRight size={16} aria-hidden="true" />
      </a>
      <button
        className="v2-menu-toggle"
        ref={button}
        aria-expanded={open}
        aria-controls="v2-mobile-menu"
        aria-label={open ? 'Fechar menu' : 'Abrir menu'}
        onClick={() => setOpen(!open)}
      >
        {open ? <X size={22} /> : <Menu size={22} />}
      </button>
      {open && (
        <nav
          className="v2-mobile-nav"
          id="v2-mobile-menu"
          aria-label="Navegação mobile"
          onClick={(e) => {
            if ((e.target as HTMLElement).closest('a')) setOpen(false)
          }}
        >
          <a href="#equipe">Nossa inteligência</a>
          <a href="#capacidades">Como funciona</a>
          <a href="#lista">
            Entrar na lista <ArrowUpRight size={16} />
          </a>
        </nav>
      )}
    </header>
  )
}
