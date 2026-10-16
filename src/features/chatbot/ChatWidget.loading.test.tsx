import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { ChatWidget } from './ChatWidget'

const panelLoad = vi.hoisted(() => {
  let resolve!: () => void
  const ready = new Promise<void>(done => { resolve = done })
  return { ready, resolve }
})

vi.mock('./ChatPanel', async () => {
  await panelLoad.ready
  return {
    default: ({ hidden }: { hidden: boolean }) => (
      <section role="dialog" aria-label="Assistente Silent Voice" hidden={hidden} />
    ),
  }
})

it('waits silently for the panel module without showing an intermediate container', async () => {
  render(<ChatWidget />)
  await userEvent.click(screen.getByRole('button', { name: 'Abrir assistente Silent Voice' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  expect(screen.queryByText(/Carregando/)).not.toBeInTheDocument()
  await act(async () => panelLoad.resolve())
  expect(await screen.findByRole('dialog', { name: 'Assistente Silent Voice' })).toBeVisible()
})
