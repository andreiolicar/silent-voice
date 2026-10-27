import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { ChatWidget } from './ChatWidget'
vi.mock('./ChatPanel', () => {
  throw new Error('simulated chunk download failure')
})
it('keeps the landing and contact available if the lazy chat module cannot load', async () => {
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  try {
    render(
      <>
        <button type="button">Controle da landing</button>
        <ChatWidget />
      </>
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Abrir assistente Silent Voice' })
    )
    expect(
      await screen.findByRole('link', { name: 'contato@silentvoice.com.br' })
    ).toHaveAttribute('href', 'mailto:contato@silentvoice.com.br')
    expect(
      screen.getByRole('button', { name: 'Controle da landing' })
    ).toBeInTheDocument()
    await userEvent.click(
      screen.getByRole('button', { name: 'Fechar painel do assistente' })
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  } finally {
    consoleError.mockRestore()
  }
})
