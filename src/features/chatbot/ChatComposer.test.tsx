import { createRef } from 'react'
import { act, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ChatComposer } from './ChatComposer'

afterEach(() => vi.unstubAllGlobals())

it('keeps an unchanged draft readable when the composer narrows and disconnects on unmount', () => {
  let onResize = () => {}
  const disconnect = vi.fn()
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback: () => void) { onResize = callback }
    observe() {}
    disconnect = disconnect
  })
  const inputRef = createRef<HTMLTextAreaElement>()
  const { unmount } = render(<ChatComposer inputRef={inputRef} active draft="Uma mensagem que ocupa mais linhas em um painel menor." busy={false} onChange={vi.fn()} onSend={vi.fn()} onStop={vi.fn()} />)
  const input = screen.getByRole('textbox', { name: 'Sua mensagem' })
  let width = 360
  let contentHeight = 24
  Object.defineProperties(input, {
    clientWidth: { get: () => width },
    scrollHeight: { get: () => contentHeight },
  })
  act(() => onResize())
  expect(input).toHaveStyle({ height: '24px', overflowY: 'hidden' })
  width = 240
  contentHeight = 72
  act(() => onResize())
  expect(input).toHaveStyle({ height: '72px', overflowY: 'hidden' })
  width = 160
  contentHeight = 144
  act(() => onResize())
  expect(input).toHaveStyle({ height: '96px', overflowY: 'auto' })
  expect(input).toHaveValue('Uma mensagem que ocupa mais linhas em um painel menor.')
  unmount()
  expect(disconnect).toHaveBeenCalledOnce()
})
