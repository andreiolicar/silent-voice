import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { runInNewContext } from 'node:vm'

// Exercise the actual early browser script with deterministic browser timing.
async function createBrowser({ reduced = false, fontsReady = true, cssReady = true, parsedReady = true, hash = '', navigation = 'navigate' } = {}) {
  const source = await readFile(new URL('../public/intro-bootstrap.js', import.meta.url), 'utf8')
  let time = 0
  let nextId = 0
  const jobs = new Map()
  const classes = new Set()
  const target = () => new EventTarget()
  const document = target()
  const window = target()
  const preference = target()
  preference.matches = reduced
  let resolveFonts
  const fonts = new Promise(resolve => { resolveFonts = resolve })
  if (fontsReady) resolveFonts()
  const curtain = { id: 'site-intro', removed: false, remove() { this.removed = true } }
  document.readyState = parsedReady ? 'complete' : 'loading'
  document.fonts = { ready: fonts }
  document.documentElement = { classList: { add: (...names) => names.forEach(name => classes.add(name)), remove: (...names) => names.forEach(name => classes.delete(name)) } }
  document.getElementById = id => id === 'site-intro' && !curtain.removed ? curtain : null
  window.matchMedia = () => preference
  window.getComputedStyle = () => ({ display: cssReady ? 'grid' : 'block' })
  window.performance = { now: () => time, getEntriesByType: () => [{ type: navigation }] }
  window.location = { hash }
  window.history = { scrollRestoration: 'auto' }
  window.scrollX = 0
  window.scrollY = 0
  window.scrollTo = (x, y) => { window.scrollX = x; window.scrollY = y }
  window.setTimeout = (run, delay) => { const id = ++nextId; jobs.set(id, { due: time + delay, run }); return id }
  window.clearTimeout = id => jobs.delete(id)
  window.requestAnimationFrame = run => window.setTimeout(run, 16)
  window.cancelAnimationFrame = window.clearTimeout
  const context = { window, document, Event, CustomEvent: class extends Event { constructor(type, options) { super(type); this.detail = options?.detail } } }
  runInNewContext(source, context)
  const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve() }
  const advance = async ms => {
    const end = time + ms
    await flush()
    while (true) {
      const next = Array.from(jobs).filter(([, job]) => job.due <= end).sort((a, b) => a[1].due - b[1].due)[0]
      if (!next) break
      const [id, job] = next
      time = job.due
      jobs.delete(id)
      job.run()
      await flush()
    }
    time = end
    await flush()
  }
  const emit = (receiver, type, properties = {}) => {
    const event = new Event(type, { cancelable: true })
    for (const [key, value] of Object.entries(properties)) Object.defineProperty(event, key, { value })
    receiver.dispatchEvent(event)
    return event
  }
  return { window, document, preference, curtain, classes, jobs, advance, emit, resolveFonts, enableCss() { cssReady = true } }
}

test('intro holds the hero until resources and the minimum presentation time are both satisfied', async () => {
  const browser = await createBrowser({ fontsReady: false })
  await browser.advance(2300)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'holding')
  browser.window.__silentVoiceIntro.heroReady()
  await browser.advance(0)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'holding')
  browser.resolveFonts()
  await browser.advance(0)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'revealing')
})

test('a cached hero still gets the full brand presentation before the curtain lifts', async () => {
  const browser = await createBrowser()
  browser.window.__silentVoiceIntro.heroReady()
  await browser.advance(2265)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'holding')
  await browser.advance(1)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'revealing')
  browser.window.__silentVoiceIntro.heroReady()
  await browser.advance(100)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'revealing')
})

test('slow CSS does not consume the visible brand presentation', async () => {
  const browser = await createBrowser({ cssReady: false, parsedReady: false })
  browser.window.__silentVoiceIntro.heroReady()
  await browser.advance(2300)
  browser.enableCss()
  browser.document.readyState = 'complete'
  browser.emit(browser.document, 'DOMContentLoaded')
  await browser.advance(4)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'holding')
  await browser.advance(2249)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'holding')
  await browser.advance(1)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'revealing')
})

test('scrollbar movement is held at the top on a fresh visit and released after the intro', async () => {
  const browser = await createBrowser()
  browser.window.scrollY = 200
  browser.emit(browser.window, 'scroll')
  assert.equal(browser.window.scrollY, 0)
  browser.window.__silentVoiceIntro.finish()
  browser.window.scrollY = 200
  browser.emit(browser.window, 'scroll')
  assert.equal(browser.window.scrollY, 200)
})

test('reduced motion initially bypasses the intro and never replays when disabled', async () => {
  const browser = await createBrowser({ reduced: true })
  assert.equal(browser.window.__silentVoiceIntro.phase, 'complete')
  assert.equal(browser.window.__silentVoiceIntro.immediate, true)
  assert.equal(browser.classes.size, 0)
  browser.preference.matches = false
  browser.emit(browser.preference, 'change')
  browser.window.__silentVoiceIntro.heroReady()
  await browser.advance(10000)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'complete')
})

test('changing reduced motion during the curtain lift finishes and clears all scheduled work', async () => {
  const browser = await createBrowser()
  browser.window.__silentVoiceIntro.heroReady()
  await browser.advance(2500)
  browser.preference.matches = true
  browser.emit(browser.preference, 'change')
  assert.equal(browser.window.__silentVoiceIntro.phase, 'complete')
  assert.equal(browser.curtain.removed, true)
  assert.equal(browser.jobs.size, 0)
  assert.equal(browser.classes.size, 0)
})

test('Tab skips the intro before focus navigation and releases scroll without replay', async () => {
  const browser = await createBrowser()
  assert.equal(browser.emit(browser.window, 'wheel', { ctrlKey: false }).defaultPrevented, true)
  assert.equal(browser.emit(browser.window, 'wheel', { ctrlKey: true }).defaultPrevented, false)
  const tab = browser.emit(browser.window, 'keydown', { key: 'Tab' })
  assert.equal(tab.defaultPrevented, false)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'complete')
  assert.equal(browser.window.__silentVoiceIntro.immediate, true)
  assert.equal(browser.emit(browser.window, 'wheel', { ctrlKey: false }).defaultPrevented, false)
  browser.window.__silentVoiceIntro.heroReady()
  await browser.advance(10000)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'complete')
  assert.equal(browser.jobs.size, 0)
})

test('curtain completion removes the overlay and releases the last-frame guards two frames later', async () => {
  const browser = await createBrowser({ navigation: 'reload' })
  browser.window.__silentVoiceIntro.heroReady()
  await browser.advance(3250)
  browser.emit(browser.document, 'animationend', { target: browser.curtain, animationName: 'intro-lift' })
  assert.equal(browser.curtain.removed, true)
  assert.equal(browser.emit(browser.window, 'wheel', { ctrlKey: false }).defaultPrevented, true)
  await browser.advance(31)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'revealing')
  await browser.advance(1)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'complete')
  assert.equal(browser.emit(browser.window, 'wheel', { ctrlKey: false }).defaultPrevented, false)
  assert.equal(browser.window.history.scrollRestoration, 'auto')
})

test('missing resources or a missing animationend cannot leave a permanent curtain', async () => {
  const browser = await createBrowser({ fontsReady: false })
  await browser.advance(3999)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'holding')
  await browser.advance(1)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'revealing')
  await browser.advance(1200)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'complete')
  assert.equal(browser.curtain.removed, true)
  assert.equal(browser.jobs.size, 0)
  browser.resolveFonts()
  browser.window.__silentVoiceIntro.heroReady()
  await browser.advance(10000)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'complete')
})

test('a direct section link keeps the target scroll and its restoration policy', async () => {
  const browser = await createBrowser({ hash: '#faq', navigation: 'reload' })
  browser.window.scrollY = 2700
  browser.emit(browser.window, 'scroll')
  assert.equal(browser.window.scrollY, 2700)
  browser.window.__silentVoiceIntro.finish()
  assert.equal(browser.window.history.scrollRestoration, 'auto')
})

test('skipping in the DOMContentLoaded task cannot recreate readiness timers', async () => {
  const browser = await createBrowser({ parsedReady: false, fontsReady: false })
  browser.document.readyState = 'complete'
  browser.emit(browser.document, 'DOMContentLoaded')
  browser.window.__silentVoiceIntro.finish()
  await browser.advance(0)
  assert.equal(browser.window.__silentVoiceIntro.phase, 'complete')
  assert.equal(browser.jobs.size, 0)
})
