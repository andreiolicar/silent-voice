import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ChatResponse } from './ChatResponse'

describe('restricted OpenUI responses', () => {
  it('renders a real card, steps and its local contact action', async () => {
    const contact = vi.fn()
    const { container } = render(
      <ChatResponse
        onContact={contact}
        content={
          'root = Answer("Como funciona", [Text("Conheça o dispositivo."), HowTo([{title: "Conecte", detail: "Abra o aplicativo."}]), ContactAction()])'
        }
      />
    )
    expect(await screen.findByText('Como funciona')).toBeVisible()
    expect(screen.getByText('Abra o aplicativo.')).toBeVisible()
    expect(container.querySelector('.openui-card')).not.toBeNull()
    await userEvent.click(
      screen.getByRole('button', { name: 'Conversar com a equipe' })
    )
    expect(contact).toHaveBeenCalledOnce()
  })
  it('keeps HTML and link-like strings as inert text', async () => {
    const { container } = render(
      <ChatResponse
        onContact={() => {}}
        content={
          'root = Answer("Detalhes", [Text("<img src=x onerror=alert(1)>"), BulletList(["javascript:alert(1)", "https://evil.example"])])'
        }
      />
    )
    expect(
      await screen.findByText('<img src=x onerror=alert(1)>')
    ).toBeVisible()
    expect(screen.getByText('javascript:alert(1)')).toBeVisible()
    expect(container.querySelector('img,a,script,iframe')).toBeNull()
  })
  it.each([
    'root = Answer("Inválido", [UnknownAction("javascript:alert(1)")])',
    'root = Answer(',
    'isto não é uma resposta válida',
    'root = Answer("Sem conteúdo", [])',
    'root = Answer("", [Text("")])',
    'root = Answer("Link proibido", [ContactAction("https://evil.example")])',
    'root = Answer("Recursivo", [Answer("Filho", [Text("não permitido")])])',
  ])(
    'recovers completed malformed or unsupported output without displaying source: %s',
    async (content) => {
      const { container } = render(
        <ChatResponse onContact={() => {}} content={content} />
      )
      expect(await screen.findByRole('status')).toHaveTextContent(
        'Não foi possível exibir esta resposta'
      )
      expect(container.textContent).not.toContain(content)
      expect(container.querySelector('a')).toBeNull()
    }
  )
  it('allows incomplete streamed content to settle before showing a fallback', () => {
    const { rerender } = render(
      <ChatResponse onContact={() => {}} streaming content={'root = Answer('} />
    )
    expect(screen.queryByText(/Não foi possível exibir/)).toBeNull()
    rerender(<ChatResponse onContact={() => {}} content={'root = Answer('} />)
    expect(screen.getByRole('status')).toHaveTextContent(
      'Não foi possível exibir'
    )
  })
})
