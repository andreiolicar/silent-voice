import { waitForApi } from '@silent-voice/http-client/readiness'
export async function registerInterest(
  email: string,
  signal: AbortSignal,
): Promise<void> {
  await waitForApi(signal)
  signal.throwIfAborted()
  const response = await fetch('/api/waitlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email.trim() }),
    signal,
  })
  if (response.status === 400) throw new Error('invalid_email')
  if (!response.ok)
    throw new Error(response.status === 429 ? 'rate_limited' : 'unconfirmed')
  const result: unknown = await response.json()
  if (
    !result ||
    typeof result !== 'object' ||
    !('registered' in result) ||
    result.registered !== true
  )
    throw new Error('invalid_receipt')
}
