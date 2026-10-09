/* Runs before React so the first paint is already the branded curtain. */
;(function () {
  if (window.__silentVoiceIntro) return

  var html = document.documentElement
  var preference = window.matchMedia('(prefers-reduced-motion: reduce)')
  var start
  var watchdog
  var phase = preference.matches ? 'complete' : 'holding'
  var immediate = preference.matches
  var timers = new Set()
  var frames = new Set()
  var listeners = []
  var resolveHero
  var hero = new Promise(function (resolve) { resolveHero = resolve })
  var restoration = window.history.scrollRestoration
  var MIN = 2250
  var WAIT_MAX = 4000

  function notify() {
    window.dispatchEvent(new CustomEvent('silentvoice:intro-state'))
  }

  function schedule(run, delay) {
    var id = window.setTimeout(function () {
      timers.delete(id)
      run()
    }, delay)
    timers.add(id)
    return id
  }

  function frame(run) {
    var id = window.requestAnimationFrame(function () {
      frames.delete(id)
      run()
    })
    frames.add(id)
  }

  function listen(target, type, handler, options) {
    target.addEventListener(type, handler, options)
    listeners.push(function () { target.removeEventListener(type, handler, options) })
  }

  function finish(skip) {
    if (phase === 'complete') return
    phase = 'complete'
    immediate = skip !== false
    timers.forEach(function (id) { window.clearTimeout(id) })
    frames.forEach(function (id) { window.cancelAnimationFrame(id) })
    timers.clear()
    frames.clear()
    listeners.forEach(function (remove) { remove() })
    listeners.length = 0
    var curtain = document.getElementById('site-intro')
    if (curtain) curtain.remove()
    html.classList.remove('intro-active', 'intro-hold', 'intro-out')
    window.history.scrollRestoration = restoration
    notify()
  }

  window.__silentVoiceIntro = {
    get phase() { return phase },
    get immediate() { return immediate },
    heroReady: function () { resolveHero() },
    finish: function () { finish(true) },
  }

  if (phase === 'complete') return
  html.classList.add('intro-active', 'intro-hold')

  // Leave the scrollbar in place: removing it would shift the whole page.
  function editable(target) {
    return !!target?.closest?.('input, textarea, select, [contenteditable]')
  }
  listen(window, 'wheel', function (event) {
    if (!event.ctrlKey) event.preventDefault()
  }, { passive: false })
  listen(window, 'touchmove', function (event) {
    if (event.touches.length === 1) event.preventDefault()
  }, { passive: false })
  listen(window, 'keydown', function (event) {
    if (event.key === 'Tab' || event.key === 'Escape') {
      finish(true)
      return
    }
    if ([' ', 'PageUp', 'PageDown', 'Home', 'End', 'ArrowUp', 'ArrowDown'].includes(event.key) && !editable(event.target)) event.preventDefault()
  }, true)
  listen(document, 'focusin', function () { finish(true) })
  listen(preference, 'change', function () {
    if (preference.matches) finish(true)
  })

  var navigation = window.performance.getEntriesByType?.('navigation')?.[0]
  if (navigation?.type !== 'back_forward' && !window.location.hash) {
    window.history.scrollRestoration = 'manual'
    window.scrollTo(0, 0)
    listen(window, 'scroll', function () {
      if (window.scrollX || window.scrollY) window.scrollTo(0, 0)
    }, { passive: true })
  }

  function capped(promise) {
    if (phase === 'complete') return Promise.resolve()
    return new Promise(function (resolve) {
      var timer = schedule(resolve, WAIT_MAX)
      Promise.resolve(promise).then(function () {
        window.clearTimeout(timer)
        timers.delete(timer)
        resolve()
      }, function () {
        window.clearTimeout(timer)
        timers.delete(timer)
        resolve()
      })
    })
  }

  var parsed = new Promise(function (resolve) {
    if (document.readyState !== 'loading') resolve()
    else listen(document, 'DOMContentLoaded', resolve, { once: true })
  })
  var fonts = parsed.then(function () {
    return capped(document.fonts ? document.fonts.ready : Promise.resolve())
  })
  var scene = parsed.then(function () { return capped(hero) })

  // Vite may put the stylesheet after this script. Count from the first frame
  // with the styled curtain, rather than including the CSS download time.
  var presented = new Promise(function (resolve) {
    function inspect() {
      if (phase !== 'holding') return
      var curtain = document.getElementById('site-intro')
      if (!curtain || window.getComputedStyle(curtain).display !== 'grid') {
        frame(inspect)
        return
      }
      start = window.performance.now()
      window.clearTimeout(watchdog)
      timers.delete(watchdog)
      watchdog = schedule(function () { finish(true) }, 6500)
      resolve()
    }
    frame(inspect)
  })

  function lift() {
    if (phase !== 'holding') return
    phase = 'revealing'
    html.classList.add('intro-out')
    notify()
    // Also release when CSS animation events are unavailable or interrupted.
    schedule(function () { finish(false) }, 1100)
  }

  Promise.all([presented, parsed, fonts, scene]).then(function () {
    if (phase === 'holding') schedule(lift, Math.max(0, MIN - (window.performance.now() - start)))
  })

  listen(document, 'animationend', function (event) {
    if (event.target.id !== 'site-intro' || event.animationName !== 'intro-lift' || phase !== 'revealing') return
    event.target.remove()
    frame(function () { frame(function () { finish(false) }) })
  })

  // A failed application bootstrap must never strand a visitor behind the cover.
  watchdog = schedule(function () { finish(true) }, 6500)
})()
