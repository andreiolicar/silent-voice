import { act, cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { StopwatchSymbol } from './StopwatchSymbol'

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

it('starts when fully admitted, holds its pose inside the viewport and rearms on exit', () => {
  const observers: { options?: IntersectionObserverInit; emit: (inside: boolean, ratio?: number) => void; disconnect: ReturnType<typeof vi.fn> }[] = []
  vi.stubGlobal('IntersectionObserver', class {
    constructor(callback: IntersectionObserverCallback, options?: IntersectionObserverInit) {
      observers.push({ options, disconnect: this.disconnect, emit: (inside, ratio = 1) =>
        callback([{ isIntersecting: inside, intersectionRatio: ratio } as IntersectionObserverEntry], this as unknown as IntersectionObserver) })
    }
    observe() {}
    disconnect = vi.fn()
  })
  const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(false)
  const { container, unmount } = render(<StopwatchSymbol />)
  const symbol = container.querySelector('.v2-stopwatch')!
  const enter = observers.find(observer => observer.options?.threshold === 1)!
  const exit = observers.find(observer => !observer.options)!
  expect(symbol).toHaveAttribute('data-started', 'false')
  act(() => enter.emit(true, .5))
  expect(symbol).toHaveAttribute('data-started', 'false')
  act(() => enter.emit(true))
  expect(symbol).toHaveAttribute('data-started', 'true')
  act(() => enter.emit(false, 0))
  expect(symbol).toHaveAttribute('data-started', 'true')
  hidden.mockReturnValue(true)
  fireEvent(document, new Event('visibilitychange'))
  expect(symbol).toHaveAttribute('data-visible', 'false')
  act(() => exit.emit(false, 0))
  expect(symbol).toHaveAttribute('data-started', 'false')
  act(() => enter.emit(true))
  expect(symbol).toHaveAttribute('data-started', 'true')
  unmount()
  observers.forEach(observer => expect(observer.disconnect).toHaveBeenCalledOnce())
})

it('keeps the decorative symbol still for reduced motion', () => {
  vi.spyOn(window, 'matchMedia').mockImplementation(query => ({
    media: query, matches: true, onchange: null,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {},
    dispatchEvent: () => true,
  }))
  const { container } = render(<StopwatchSymbol />)
  const symbol = container.querySelector('.v2-stopwatch')!
  expect(symbol).toHaveAttribute('data-started', 'false')
  expect(symbol).toHaveAttribute('aria-hidden', 'true')
})
