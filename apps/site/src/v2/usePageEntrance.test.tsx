import { act, cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { usePageEntrance } from './usePageEntrance'

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

function Content() {
  const ref = usePageEntrance()
  return <div ref={ref}><div data-reveal="0"><button>Explorar</button></div><p data-reveal="1">Descrição</p></div>
}

function observerMock() {
  let emit: (element: Element, ratio: number) => void = () => {}
  const unobserve = vi.fn()
  const disconnect = vi.fn()
  vi.stubGlobal('IntersectionObserver', class {
    constructor(callback: IntersectionObserverCallback) {
      emit = (target, intersectionRatio) => callback([
        { target, isIntersecting: intersectionRatio > 0, intersectionRatio } as IntersectionObserverEntry,
      ], this as unknown as IntersectionObserver)
    }
    observe() {}
    unobserve = unobserve
    disconnect = disconnect
  })
  return { emit: (element: Element, ratio: number) => act(() => emit(element, ratio)), unobserve, disconnect }
}

it('reveals admitted elements once and disconnects on unmount', () => {
  const observer = observerMock()
  const { container, unmount } = render(<Content />)
  const element = container.querySelector('[data-reveal]')!
  observer.emit(element, .05)
  expect(element).toHaveAttribute('data-reveal-pending')
  observer.emit(element, .2)
  expect(element).toHaveAttribute('data-revealed', 'animated')
  expect(element).not.toHaveAttribute('data-reveal-pending')
  expect(observer.unobserve).toHaveBeenCalledWith(element)
  observer.emit(element, 0)
  expect(element).toHaveAttribute('data-revealed', 'animated')
  unmount()
  expect(observer.disconnect).toHaveBeenCalledOnce()
})

it('immediately shows the container of a focused control before intersection', () => {
  observerMock()
  const { container, getByRole } = render(<Content />)
  fireEvent.focusIn(getByRole('button'))
  expect(container.querySelector('[data-reveal]')).toHaveAttribute('data-revealed', 'immediate')
  expect(container.querySelector('[data-reveal]')).not.toHaveAttribute('data-reveal-pending')
})

it('keeps every element visible without animation for reduced motion', () => {
  vi.spyOn(window, 'matchMedia').mockImplementation(query => ({
    media: query, matches: true, onchange: null,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => true,
  }))
  const { container } = render(<Content />)
  container.querySelectorAll('[data-reveal]').forEach(element => {
    expect(element).toHaveAttribute('data-revealed', 'immediate')
    expect(element).not.toHaveAttribute('data-reveal-pending')
  })
})
