import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LazyMotion, domAnimation } from 'motion/react'
import { expect, it, vi } from 'vitest'
import { Faq } from './Faq'

vi.mock('../entrance', () => ({ useReducedMotionPreference: () => true }))

function renderFaq() {
  render(<LazyMotion features={domAnimation} strict><Faq /></LazyMotion>)
}

it('opens one answer at a time and supports closing the answer with the keyboard', async () => {
  renderFaq()
  const user = userEvent.setup()
  const first = screen.getByRole('button', { name: 'O que é o Silent Voice?' })
  const second = screen.getByRole('button', { name: 'Para quem ele foi pensado?' })
  expect(first).toHaveAttribute('aria-expanded', 'true')
  expect(second).toHaveAttribute('aria-expanded', 'false')

  await user.click(second)
  expect(first).toHaveAttribute('aria-expanded', 'false')
  expect(second).toHaveAttribute('aria-expanded', 'true')
  expect(document.getElementById(second.getAttribute('aria-controls')!)).toHaveAttribute('aria-hidden', 'false')

  await user.keyboard('{Enter}')
  expect(second).toHaveAttribute('aria-expanded', 'false')
  expect(screen.getAllByRole('button').every(button => button.getAttribute('aria-expanded') === 'false')).toBe(true)
  await user.keyboard(' ')
  expect(second).toHaveAttribute('aria-expanded', 'true')
})

it('keeps links inside closed answers out of navigation and exposes working contact links when opened', async () => {
  renderFaq()
  const user = userEvent.setup()
  expect(screen.queryByRole('link', { name: 'lista de interesse' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Como posso acompanhar os próximos passos?' }))
  expect(screen.getByRole('link', { name: 'lista de interesse' })).toHaveAttribute('href', '#lista')
  await user.click(screen.getByRole('button', { name: 'Como posso falar com a equipe?' }))
  expect(screen.queryByRole('link', { name: 'lista de interesse' })).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'contato@silentvoice.com.br' })).toHaveAttribute('href', 'mailto:contato@silentvoice.com.br')
})
