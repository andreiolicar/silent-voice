import type { ServerConfig } from './config.ts'

/** Only server-configured origins are trusted; injected configs remain exact-only. */
export function isAllowedOrigin(
  origin: unknown,
  config: ServerConfig
): boolean {
  return (
    typeof origin === 'string' &&
    (origin === config.origin ||
      config.allowedOrigins?.includes(origin) === true)
  )
}
