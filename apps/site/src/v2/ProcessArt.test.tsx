import { act, fireEvent, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ProcessArt } from './ProcessArt'

afterEach(() => vi.restoreAllMocks())

it('pauses each diagram offscreen or while the page is hidden without remounting its artwork', () => {
  const observers = new Map<Element, (visible: boolean) => void>()
  const disconnect = vi.fn()
  vi.stubGlobal('IntersectionObserver', class {
    constructor(private callback: IntersectionObserverCallback) {}
    observe(target: Element) {
      observers.set(target, (visible) => this.callback(
        [{ target, isIntersecting: visible } as IntersectionObserverEntry],
        this as unknown as IntersectionObserver,
      ))
    }
    disconnect = disconnect
  })
  const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(false)
  const { container, unmount } = render(<>
    <ProcessArt kind="capture" />
    <ProcessArt kind="fusion" />
    <ProcessArt kind="voice" />
  </>)
  const diagrams = [...container.querySelectorAll<HTMLElement>('.v2-process-art')]
  const canvas = diagrams[0]!.firstElementChild
  const states = () => diagrams.map((e) => e.style.getPropertyValue('--process-play-state'))
  expect(states()).toEqual(['paused', 'paused', 'paused'])
  act(() => observers.forEach((visible) => visible(true)))
  expect(states()).toEqual(['running', 'running', 'running'])
  act(() => observers.get(diagrams[0]!)!(false))
  expect(states()).toEqual(['paused', 'running', 'running'])
  hidden.mockReturnValue(true)
  fireEvent(document, new Event('visibilitychange'))
  expect(states()).toEqual(['paused', 'paused', 'paused'])
  hidden.mockReturnValue(false)
  fireEvent(document, new Event('visibilitychange'))
  expect(states()).toEqual(['paused', 'running', 'running'])
  act(() => observers.get(diagrams[0]!)!(true))
  expect(states()).toEqual(['running', 'running', 'running'])
  expect(diagrams[0]!.firstElementChild).toBe(canvas)
  unmount()
  expect(disconnect).toHaveBeenCalledTimes(3)
})

it('keeps decorative motion paused when reduced motion is requested', () => {
  vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
    media: query,
    matches: true,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent: () => true,
  }))
  const { container } = render(<>
    <ProcessArt kind="capture" />
    <ProcessArt kind="fusion" />
    <ProcessArt kind="voice" />
  </>)
  for (const diagram of container.querySelectorAll<HTMLElement>('.v2-process-art')) {
    expect(diagram.style.getPropertyValue('--process-play-state')).toBe('paused')
    expect(diagram).toHaveAttribute('aria-hidden', 'true')
  }
})
