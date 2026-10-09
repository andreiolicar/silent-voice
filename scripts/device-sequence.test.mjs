import { test } from 'node:test'
import assert from 'node:assert/strict'
import { sampleSequence, createSequenceSession, SEQUENCE_EASE, TOGGLE_SECONDS } from '../src/components/device-integrated/sequence.ts'
import { JSAnimation } from 'motion-dom'

function setup(reduced = false) {
  const values = { entrance: 0, expansion: 0 }
  const jobs = []
  const stopped = []
  const session = createSequenceSession({
    reduced,
    read: channel => values[channel],
    write: (channel, value) => { values[channel] = value },
    start: (channel, spec) => {
      const job = { channel, ...spec }; jobs.push(job)
      return { stop() { stopped.push({ channel, value: values[channel] }); values[channel] = -100 } }
    },
  })
  session.mount(); session.setEntrance(true); session.setVisible(true); session.setIntersection(.5)
  const finish = () => {
    const job = jobs.at(-1); values[job.channel] = job.to; job.onComplete()
  }
  const arrive = () => { session.decoded(); if (!reduced) finish() }
  return { session, values, jobs, stopped, finish, arrive }
}

test('entrance ends closed and component movement waits for 20% expansion', () => {
  assert.equal(sampleSequence(0, 0).groupY, 115)
  assert.equal(sampleSequence(1, 0).groupY, 0)
  assert.equal(sampleSequence(1, 0).covers, 0)
  assert.equal(sampleSequence(1, .2).components, 0)
  assert.ok(sampleSequence(1, .3).components > 0)
  assert.equal(sampleSequence(1, .8).covers, 1)
  assert.equal(sampleSequence(1, 1).components, 1)
})
test('waits for entrance, decode and 35%; no queued clicks and no automatic opening', () => {
  const s = setup(); s.session.setEntrance(false); s.session.toggleExpanded(); s.session.decoded()
  assert.equal(s.jobs.length, 0); s.session.setEntrance(true); assert.equal(s.jobs.length, 1)
  s.session.toggleExpanded(); assert.equal(s.session.snapshot().expanded, false)
  s.finish(); assert.equal(s.session.snapshot().phase, 'closed'); assert.equal(s.jobs.length, 1)
  s.session.setIntersection(0); s.session.setIntersection(1); assert.equal(s.jobs.length, 1)
})
test('opening and closing use 1.6s with an exact centered closed endpoint', () => {
  const s = setup(); s.arrive(); s.session.toggleExpanded()
  assert.equal(s.jobs.at(-1).duration, 1.6); assert.equal(s.session.snapshot().phase, 'opening')
  s.finish(); assert.equal(s.session.snapshot().phase, 'open'); assert.equal(s.values.expansion, 1)
  s.session.toggleExpanded(); assert.equal(s.jobs.at(-1).to, 0); s.finish()
  assert.equal(s.session.snapshot().phase, 'closed'); assert.equal(s.values.expansion, 0)
  assert.equal(s.values.entrance, 1)
})
test('reversal preserves current position and takes proportional duration', () => {
  const s = setup(); s.arrive(); s.session.toggleExpanded(); s.values.expansion = .4
  const oldCompletion = s.jobs.at(-1).onComplete
  s.session.toggleExpanded(); assert.equal(s.values.expansion, .4)
  assert.equal(s.jobs.at(-1).from, .4); assert.ok(Math.abs(s.jobs.at(-1).duration - .64) < 1e-8)
  assert.equal(s.session.snapshot().phase, 'closing'); oldCompletion(); assert.equal(s.values.expansion, .4)
  s.values.expansion = .2; s.session.toggleExpanded(); assert.equal(s.values.expansion, .2)
  assert.ok(Math.abs(s.jobs.at(-1).duration - 1.28) < 1e-8)
})
test('scroll and hidden pause preserve both clocks; resume obeys 20–35 hysteresis', () => {
  const s = setup(); s.session.decoded(); s.values.entrance = .4
  s.session.setIntersection(.25); assert.equal(s.jobs.length, 1)
  s.session.setIntersection(.19); assert.equal(s.values.entrance, .4)
  s.session.setIntersection(.3); assert.equal(s.jobs.length, 1)
  s.session.setIntersection(.35); assert.equal(s.jobs.length, 2); s.finish()
  s.session.toggleExpanded(); s.values.expansion = .6; s.session.setVisible(false)
  assert.equal(s.values.expansion, .6); const n = s.jobs.length
  s.session.setIntersection(.25); s.session.setVisible(true); assert.equal(s.jobs.length, n)
  s.session.setIntersection(.35); assert.equal(s.jobs.at(-1).from, .6)
  assert.equal(s.jobs.at(-1).to, 1)
})
test('first entrance cannot begin in the admission band', () => {
  const s = setup(); s.session.setIntersection(.25); s.session.decoded(); assert.equal(s.jobs.length, 0)
  s.session.setIntersection(.35); assert.equal(s.jobs.length, 1)
})
test('reversing within the admitted 20–35% band continues without a scroll', () => {
  const s = setup(); s.arrive(); s.session.toggleExpanded(); s.values.expansion = .5
  s.session.setIntersection(.25); const n = s.jobs.length
  s.session.toggleExpanded()
  assert.equal(s.jobs.length, n + 1); assert.equal(s.jobs.at(-1).to, 0)
  assert.equal(s.session.snapshot().running, true)
})
test('real Motion clock preserves the 20% stagger and remaining time after suspension', () => {
  const animation = new JSAnimation({ keyframes: [0, 1], duration: TOGGLE_SECONDS * 1000,
    ease: SEQUENCE_EASE.expansion, autoplay: false })
  try {
    const at20 = animation.sample(320).value
    assert.equal(sampleSequence(1, at20).components, 0)
    const midway = animation.sample(800).value
    const s = setup(); s.arrive(); s.session.toggleExpanded(); s.values.expansion = midway
    s.session.setVisible(false); s.session.setVisible(true)
    assert.ok(Math.abs(s.jobs.at(-1).duration - .8) < .001)
  } finally { animation.stop() }
})
test('keyboard skips only the rise, never opens automatically or restarts expansion', () => {
  const s = setup(); s.session.skipEntrance(); assert.equal(s.values.entrance, 1)
  assert.equal(s.session.snapshot().canInteract, false); s.session.decoded()
  assert.equal(s.session.snapshot().phase, 'closed'); assert.equal(s.jobs.length, 0)
  s.session.toggleExpanded(); s.values.expansion = .5; s.session.skipEntrance()
  assert.equal(s.jobs.length, 1); assert.equal(s.values.expansion, .5)
})
test('reduced initial is closed but interactive, toggles instantly and can later animate', () => {
  const s = setup(true); s.arrive(); assert.equal(s.session.snapshot().phase, 'closed')
  assert.equal(s.jobs.length, 0); s.session.toggleExpanded(); assert.equal(s.values.expansion, 1)
  assert.equal(s.session.snapshot().phase, 'open'); s.session.toggleExpanded(); assert.equal(s.values.expansion, 0)
  s.session.setReduced(false); assert.equal(s.jobs.length, 0); s.session.toggleExpanded(); assert.equal(s.jobs.length, 1)
})
test('reduced during opening or closing completes the requested pose without replay', () => {
  for (const closing of [false, true]) {
    const s = setup(); s.arrive(); s.session.toggleExpanded()
    if (closing) { s.finish(); s.session.toggleExpanded() }
    s.values.expansion = .5; s.session.setReduced(true)
    assert.equal(s.values.expansion, closing ? 0 : 1)
    const n = s.jobs.length; s.session.setReduced(false); assert.equal(s.jobs.length, n)
  }
})
test('errors fall back closed and late decode/completion cannot revive disposed sessions', () => {
  const s = setup(); s.arrive(); s.session.toggleExpanded(); const done = s.jobs.at(-1).onComplete
  s.session.fail(); assert.equal(s.values.expansion, 0); assert.equal(s.session.snapshot().phase, 'error')
  assert.equal(s.session.snapshot().canInteract, false); const n = s.jobs.length
  s.session.decoded(); s.session.toggleExpanded(); done(); assert.equal(s.jobs.length, n)
  const late = setup(); late.session.unmount(); late.session.decoded(); assert.equal(late.jobs.length, 0)
  const active = setup(); active.arrive(); active.session.toggleExpanded(); const stale = active.jobs.at(-1).onComplete
  active.values.expansion = .3; active.session.unmount(); stale(); assert.equal(active.values.expansion, .3)
})
test('repeated complete cycles never replay entrance or accumulate position error', () => {
  const s = setup(); s.arrive()
  for (let i = 0; i < 10; i++) {
    s.session.toggleExpanded(); s.finish(); s.session.toggleExpanded(); s.finish()
    assert.equal(s.values.expansion, 0); assert.equal(s.values.entrance, 1)
  }
  assert.equal(s.jobs.filter(job => job.channel === 'entrance').length, 1)
})

test('both centered poses and every intermediate frame fit the card with fixed scale', async () => {
  const { readFile } = await import('node:fs/promises')
  const geometry = JSON.parse(await readFile(new URL('../src/components/device-integrated/geometry.json', import.meta.url), 'utf8'))
  assert.deepEqual(geometry.layers.map(layer => layer.id), ['housing','raspberry-pi','esp32','myoware','lid-main','lid-small'])
  for (let step = 0; step <= 100; step++) {
    const pose = sampleSequence(1, step / 100)
    const tx = geometry.closedTranslate[0] + (geometry.openTranslate[0] - geometry.closedTranslate[0]) * pose.centering
    const ty = geometry.closedTranslate[1] + (geometry.openTranslate[1] - geometry.closedTranslate[1]) * pose.centering
    const bounds = geometry.layers.map(layer => {
      const p = layer.kind === 'cover' ? pose.covers : layer.kind === 'component' ? pose.components : 0
      return layer.bounds.map((n, axis) => geometry.scale * (n + layer.offset[axis % 2] * p) + (axis % 2 ? ty : tx))
    })
    const box = [Math.min(...bounds.map(b=>b[0])),Math.min(...bounds.map(b=>b[1])),Math.max(...bounds.map(b=>b[2])),Math.max(...bounds.map(b=>b[3]))]
    for (const canvasWidth of [648, 568]) {
      const ratio = canvasWidth / 648
      assert.ok(Math.min(box[0], box[1], 648-box[2], 440-box[3]) * ratio >= 24 - 1e-6,
        `24 CSS px margins at canvas width ${canvasWidth}, frame ${step}`)
    }
    if (step === 0 || step === 100) {
      assert.ok(Math.abs((box[0]+box[2])/2 - 324) < 1e-6)
      assert.ok(Math.abs((box[1]+box[3])/2 - 220) < 1e-6)
    }
  }
})

test('assembly guides stay attached throughout opening, reversal and closing', async () => {
  const { sampleDeviceGuide } = await import('../src/components/device-integrated/sequence.ts')
  const guide = { housingAnchor: [125, 146], lidAnchor: [125, 146] }
  const offset = [-80, 94]
  assert.deepEqual(sampleDeviceGuide(guide, offset, 0), { x1: 125, y1: 146, x2: 125, y2: 146, opacity: 0 })
  assert.equal(sampleDeviceGuide(guide, offset, .1).opacity, 0)
  assert.equal(sampleDeviceGuide(guide, offset, .4).opacity, 1)
  assert.ok(Math.abs(sampleDeviceGuide(guide, offset, .25).opacity - .5) < 1e-8)
  for (const expansion of [0, .15, .4, .8, 1, .8, .4, .2, 0]) {
    const cover = sampleSequence(1, expansion).covers
    const line = sampleDeviceGuide(guide, offset, cover)
    assert.equal(line.x1, 125); assert.equal(line.y1, 146)
    assert.equal(line.x2, 125 - 80 * cover); assert.equal(line.y2, 146 + 94 * cover)
    assert.ok(line.opacity >= 0 && line.opacity <= 1)
  }
})

test('four assembly guides reference existing covers and remain within framed poses', async () => {
  const { readFile } = await import('node:fs/promises')
  const { sampleDeviceGuide } = await import('../src/components/device-integrated/sequence.ts')
  const geometry = JSON.parse(await readFile(new URL('../src/components/device-integrated/geometry.json', import.meta.url), 'utf8'))
  assert.equal(geometry.guides.length, 4)
  for (const id of ['lid-main', 'lid-small']) assert.equal(geometry.guides.filter(g => g.coverId === id).length, 2)
  for (const guide of geometry.guides) {
    const cover = geometry.layers.find(layer => layer.id === guide.coverId)
    assert.equal(cover.kind, 'cover')
    for (let step = 0; step <= 100; step++) {
      const pose = sampleSequence(1, step / 100)
      const line = sampleDeviceGuide(guide, cover.offset, pose.covers)
      const center = geometry.closedTranslate.map((v, i) => v + (geometry.openTranslate[i] - v) * pose.centering)
      for (const [x, y] of [[line.x1, line.y1], [line.x2, line.y2]]) {
        const px = x * geometry.scale + center[0], py = y * geometry.scale + center[1]
        assert.ok(Math.min(px, py, 648 - px, 440 - py) * 568 / 648 >= 24)
      }
    }
  }
})
