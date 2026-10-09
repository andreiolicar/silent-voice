const progress = (time: number, start: number, duration: number) =>
  Math.max(0, Math.min(1, (time - start) / duration))
const easeOut = (value: number) => 1 - (1 - value) ** 3
const smooth = (value: number) => value * value * (3 - 2 * value)

function bubble(time: number, start: number, lineStarts: number[]) {
  const entry = easeOut(progress(time, start, .35))
  return {
    opacity: easeOut(progress(time, start, .16)),
    scale: .9 + entry * .1,
    y: 6 * (1 - entry),
    lines: lineStarts.map(start => easeOut(progress(time, start, .22))),
  }
}

/** The handset retains its eight-second cycle independently of the message entrance. */
export function samplePhoneRing(seconds: number) {
  const time = ((seconds % 8) + 8) % 8
  let phone = 0
  if (time > 1 && time < 1.6) {
    const angles = [0, -8, 8, -6, 6, 0]
    const position = (time - 1) / .12
    const index = Math.min(4, Math.floor(position))
    phone = angles[index] + (angles[index + 1] - angles[index]) * smooth(position - index)
  }
  return phone
}

export const CONVERSATION_DURATION = 3.5

/** Reveal the messages once and hold their completed composition. */
export function sampleConversation(seconds: number) {
  const time = Math.max(0, seconds)
  return {
    incoming: bubble(time, 1.75, [2.05, 2.16, 2.27]),
    reply: bubble(time, 2.8, [3.1, 3.22]),
  }
}
