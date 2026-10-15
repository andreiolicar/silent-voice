import { isAbsolute, relative, resolve, sep } from 'node:path'

export type ServerConfig = {
  port: number
  origin: string
  allowedOrigins?: readonly string[]
  databasePath: string
  sessionSecret: string
  secureCookies: boolean
  mistralApiKey?: string
  mistralModel: string
  chatTimeoutMs: number
  idleTimeoutMs: number
}
export function loadConfig(): ServerConfig {
  const databasePath = process.env.SQLITE_PATH || 'data/silent-voice.sqlite'
  const publicRelative = relative(resolve('public'), resolve(databasePath))
  if (
    !publicRelative ||
    (!publicRelative.startsWith(`..${sep}`) &&
      publicRelative !== '..' &&
      !isAbsolute(publicRelative))
  ) {
    throw new Error(
      'SQLITE_PATH must remain outside the public asset directory'
    )
  }
  const production = process.env.NODE_ENV === 'production'
  const origin = process.env.APP_ORIGIN || 'http://127.0.0.1:5173'
  const allowedOrigins = [origin]
  if ((process.env.NODE_ENV || 'development') === 'development') {
    try {
      const local = new URL(origin)
      if (
        local.origin === origin &&
        ['http:', 'https:'].includes(local.protocol) &&
        ['localhost', '127.0.0.1'].includes(local.hostname)
      ) {
        local.hostname =
          local.hostname === 'localhost' ? '127.0.0.1' : 'localhost'
        allowedOrigins.push(local.origin)
      }
    } catch {
      /* Invalid configured origins remain exact-only. */
    }
  }
  const secret = process.env.SESSION_SECRET
  if (production && (!secret || secret.length < 32))
    throw new Error('SESSION_SECRET must contain at least 32 characters')
  return {
    port: Number(process.env.PORT || 3001),
    origin,
    allowedOrigins,
    databasePath,
    sessionSecret:
      secret || 'local-development-only-change-before-deploy-please',
    secureCookies: production,
    mistralApiKey: process.env.MISTRAL_API_KEY,
    mistralModel: process.env.MISTRAL_MODEL || 'mistral-small-2603',
    chatTimeoutMs: 45_000,
    idleTimeoutMs: 15_000,
  }
}
