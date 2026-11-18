import { useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ProductHero } from './ProductHero'
import { AgentTeam } from './AgentTeam'
import type { AgentId } from './agents'

afterEach(() => { cleanup(); delete window.__silentVoiceIntro })

function HeroWithTeam() {
  const [request, setRequest] = useState<{ id: AgentId }>()
  return <><ProductHero onSelectAgent={(id) => setRequest({ id })} /><AgentTeam requestedAgent={request} /></>
}

it('links to the team and selects the requested agent, including after a manual change', () => {
  render(<HeroWithTeam />)
  for (const name of ['Lia', 'Ravi', 'Caio', 'Lia']) {
    const link = screen.getByRole('link', { name: new RegExp(`Conhecer ${name}:`) })
    expect(link).toHaveAttribute('href', '#equipe')
    fireEvent.click(link)
    expect(screen.getByRole('tab', { name: new RegExp(`^${name} —`) })).toHaveAttribute('aria-selected', 'true')
  }
  fireEvent.click(screen.getByRole('tab', { name: /^Ravi —/ }))
  fireEvent.click(screen.getByRole('link', { name: /^Conhecer Lia:/ }))
  expect(screen.getByRole('tab', { name: /^Lia —/ })).toHaveAttribute('aria-selected', 'true')
})

it('keeps the entrance finished when focus moves between hero cards', () => {
  window.__silentVoiceIntro = { phase: 'holding', immediate: false, heroReady() {}, finish() {} }
  const { container } = render(<ProductHero />)
  const hero = container.querySelector('.v2-product-hero')!
  expect(hero).toHaveAttribute('data-immediate', 'false')
  const caio = screen.getByRole('link', { name: /^Conhecer Caio:/ })
  fireEvent.focusIn(caio)
  fireEvent.focusOut(caio)
  fireEvent.focusIn(screen.getByRole('link', { name: /^Conhecer Lia:/ }))
  expect(hero).toHaveAttribute('data-immediate', 'true')
})

it('releases the intro and preserves the explanation if the portrait fails', () => {
  const heroReady = vi.fn()
  window.__silentVoiceIntro = { phase: 'holding', immediate: false, heroReady, finish() {} }
  render(<ProductHero />)
  fireEvent.error(screen.getByAltText(/Pessoa usando a neckband/))
  expect(heroReady).toHaveBeenCalled()
  expect(screen.getByAltText('Dispositivo Silent Voice fechado.')).toBeVisible()
  expect(screen.getByRole('link', { name: /^Conhecer Caio:/ })).toBeVisible()
  expect(screen.queryByRole('list', { name: 'Da expressão à voz' })).not.toBeInTheDocument()
  delete window.__silentVoiceIntro
})
