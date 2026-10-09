import { test } from 'node:test'
import assert from 'node:assert/strict'
import { CONVERSATION_DURATION, sampleConversation, samplePhoneRing } from '../src/components/cards/conversation.ts'

test('telephone rings only before the first message and settles without drift', () => {
  assert.equal(samplePhoneRing(.9), 0)
  assert.ok(Math.abs(samplePhoneRing(1.12)) > 0)
  assert.equal(samplePhoneRing(1.6), 0)
  assert.equal(samplePhoneRing(6), 0)
  assert.equal(samplePhoneRing(9.12), samplePhoneRing(1.12))
  for (let t=0;t<8;t+=.01) assert.ok(Math.abs(samplePhoneRing(t))<=8)
})
test('incoming and reply are staggered, with their text revealed after their bubbles', () => {
  assert.equal(sampleConversation(1.74).incoming.opacity, 0)
  assert.ok(sampleConversation(1.85).incoming.opacity>0)
  assert.deepEqual(sampleConversation(1.85).incoming.lines,[0,0,0])
  assert.ok(sampleConversation(2.1).incoming.lines[0]>0)
  assert.equal(sampleConversation(2.1).incoming.lines[1],0)
  assert.equal(sampleConversation(2.79).reply.opacity,0)
  assert.ok(sampleConversation(2.9).reply.opacity>0)
  assert.deepEqual(sampleConversation(2.9).reply.lines,[0,0])
  const held=sampleConversation(4)
  assert.equal(held.incoming.opacity,1)
  assert.equal(held.reply.opacity,1)
  assert.deepEqual(held.incoming.lines,[1,1,1])
  assert.deepEqual(held.reply.lines,[1,1])
})
test('messages remain fully visible after their entrance without fading or restarting', () => {
  const complete = sampleConversation(CONVERSATION_DURATION)
  assert.equal(complete.incoming.opacity, 1)
  assert.equal(complete.reply.opacity, 1)
  assert.deepEqual(complete.incoming.lines, [1, 1, 1])
  assert.deepEqual(complete.reply.lines, [1, 1])
  for (const seconds of [7.45, 7.7, 8, 11, 16, 60]) {
    assert.deepEqual(sampleConversation(seconds), complete)
  }
})
