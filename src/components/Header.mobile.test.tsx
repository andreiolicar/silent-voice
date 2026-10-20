import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { LazyMotion, domAnimation } from 'motion/react'
import { Header } from './Header'
vi.mock('../entrance', () => ({ useEntrance: () => () => ({}) }))
it('opens mobile navigation with every existing item and closes with Escape', () => {
  render(<LazyMotion features={domAnimation} strict><Header /></LazyMotion>)
  const toggle = screen.getByRole('button', { name: 'Abrir menu' })
  expect(toggle).toHaveAttribute('aria-expanded', 'false')
  fireEvent.click(toggle)
  expect(screen.getByRole('button', { name: 'Fechar menu' })).toHaveAttribute('aria-expanded', 'true')
  const panel = document.getElementById('mobile-navigation')!
  for (const label of ['Início','Institucional','Serviços','Investimento','Contato','Participe']) expect(panel.textContent).toContain(label)
  fireEvent.keyDown(panel, { key:'Escape' })
  expect(screen.getByRole('button', { name:'Abrir menu' })).toHaveAttribute('aria-expanded','false')
})
