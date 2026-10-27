import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { GreenButton } from './Button'

it('submits a form when used as an enabled submit control', async () => {
  const submit = vi.fn((event) => event.preventDefault())
  render(
    <form onSubmit={submit}>
      <GreenButton type="submit">Entrar</GreenButton>
    </form>
  )
  const button = screen.getByRole('button', { name: 'Entrar' })
  expect(button).not.toHaveAttribute('aria-disabled', 'true')
  await userEvent.click(button)
  expect(submit).toHaveBeenCalledOnce()
})

it('prevents a repeated form submission while disabled', async () => {
  const submit = vi.fn((event) => event.preventDefault())
  render(
    <form onSubmit={submit}>
      <GreenButton type="submit" disabled>
        Entrando…
      </GreenButton>
    </form>
  )
  const button = screen.getByRole('button', { name: 'Entrando…' })
  expect(button).toBeDisabled()
  await userEvent.click(button)
  expect(submit).not.toHaveBeenCalled()
})
