import { samplePhoneRing } from './conversation.ts'

export const EXPRESSION_CYCLE_DURATION = 8

/** Wait for all three entrances, then ring from left to right with a short rest. */
export function sampleExpressionWiggle(seconds: number, index: 0 | 1 | 2) {
  const time = ((seconds % EXPRESSION_CYCLE_DURATION) + EXPRESSION_CYCLE_DURATION) % EXPRESSION_CYCLE_DURATION
  const start = 1.9 + index * .72
  if (time <= start || time >= start + .6) return 0
  return samplePhoneRing(1 + time - start)
}
