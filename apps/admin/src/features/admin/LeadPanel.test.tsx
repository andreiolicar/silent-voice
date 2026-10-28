// @vitest-environment jsdom
import { afterEach, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { LeadPanel } from './LeadPanel'
import type { AdminRequest } from './admin-api'
import type { LeadDetail } from '@silent-voice/contracts/leads'

const detail: LeadDetail = {
  lead: {
    id: 'contact-1',
    name: 'Ana Souza',
    email: 'ana@example.test',
    objective: 'Conhecer as possibilidades do dispositivo.',
    status: 'new',
    version: 1,
    createdAt: '2026-10-15T12:00:00Z',
    updatedAt: '2026-10-15T12:00:00Z',
    duplicateEmail: false,
  },
  notes: [],
}
const request = (async () => detail) as AdminRequest

afterEach(() => {
  cleanup()
  document.body.style.overflow = ''
})

it('lets the inline inspector share keyboard navigation with the table', async () => {
  document.body.style.overflow = 'auto'
  render(
    <LeadPanel
      mode="inline"
      id="contact-1"
      request={request}
      draft={{ text: 'Próximo passo' }}
      updateDraft={() => undefined}
      close={() => undefined}
      restoreFocus={() => undefined}
      onChange={() => undefined}
    />
  )
  const dialog = await screen.findByRole('dialog', { name: 'Contato de Ana Souza' })
  expect(dialog).toHaveAttribute('aria-modal', 'false')
  expect(document.body.style.overflow).toBe('auto')
  const lastControl = screen.getByRole('button', { name: 'Adicionar anotação' })
  lastControl.focus()
  const allowed = fireEvent.keyDown(lastControl, { key: 'Tab', cancelable: true })
  expect(allowed).toBe(true)
  expect(lastControl).toHaveFocus()
})
