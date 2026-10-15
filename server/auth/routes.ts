import cookie from '@fastify/cookie'
import session from '@fastify/session'
import { randomBytes, timingSafeEqual } from 'node:crypto'
import { z } from 'zod'
import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify'
import type Database from 'better-sqlite3'
import type { ServerConfig } from '../config.ts'
import { isAllowedOrigin } from '../origin.ts'
import { createSessionStore } from './store.ts'
import { verifyPassword } from './password.ts'

declare module 'fastify' {
  interface Session {
    adminId?: string
    adminEmail?: string
    csrfToken?: string
  }
}
const token = () => randomBytes(32).toString('hex')
export function requireOrigin(
  request: FastifyRequest,
  reply: FastifyReply,
  config: ServerConfig
): boolean {
  if (!isAllowedOrigin(request.headers.origin, config)) {
    reply.code(403).send({ error: 'Solicitação não permitida.' })
    return false
  }
  return true
}
export function requireCsrf(
  request: FastifyRequest,
  reply: FastifyReply
): boolean {
  const supplied = request.headers['x-csrf-token']
  const expected = request.session.csrfToken
  if (
    typeof supplied !== 'string' ||
    !/^[a-f0-9]{64}$/.test(supplied) ||
    !expected ||
    supplied.length !== expected.length ||
    !timingSafeEqual(Buffer.from(supplied), Buffer.from(expected))
  ) {
    reply.code(403).send({ error: 'Solicitação não permitida.' })
    return false
  }
  return true
}
export async function requireAdmin(
  request: FastifyRequest,
  reply: FastifyReply
): Promise<void> {
  if (!request.session.adminId || !request.session.adminEmail)
    reply.code(401).send({ error: 'Autenticação necessária.' })
}
export async function registerAuthRoutes(
  app: FastifyInstance,
  db: Database.Database,
  config: ServerConfig
): Promise<void> {
  await app.register(cookie)
  await app.register(session, {
    secret: config.sessionSecret,
    cookieName: 'sv_admin',
    saveUninitialized: false,
    rolling: false,
    store: createSessionStore(db),
    cookie: {
      path: '/',
      httpOnly: true,
      sameSite: 'strict',
      secure: config.secureCookies,
      maxAge: 8 * 60 * 60 * 1000,
    },
  })
  app.get('/api/auth/csrf', async (request) => {
    request.session.csrfToken ||= token()
    return { csrfToken: request.session.csrfToken }
  })
  app.get(
    '/api/auth/session',
    { preHandler: requireAdmin },
    async (request) => ({
      user: { email: request.session.adminEmail! },
      csrfToken: request.session.csrfToken!,
    })
  )
  const login = z
    .object({
      email: z.string().trim().toLowerCase().max(254).email(),
      password: z.string().min(1).max(256),
    })
    .strict()
  const findUser = db.prepare(
    'SELECT id, email, password_hash FROM admin_users WHERE email = ?'
  )
  app.post(
    '/api/auth/login',
    { config: { rateLimit: { max: 5, timeWindow: '15 minutes' } } },
    async (request, reply) => {
      if (
        !requireOrigin(request, reply, config) ||
        !requireCsrf(request, reply)
      )
        return
      const parsed = login.safeParse(request.body)
      if (!parsed.success)
        return reply.code(400).send({ error: 'Dados inválidos.' })
      const user = findUser.get(parsed.data.email) as
        { id: string; email: string; password_hash: string } | undefined
      const valid = await verifyPassword(
        parsed.data.password,
        user?.password_hash || ''
      )
      if (!user || !valid)
        return reply.code(401).send({ error: 'E-mail ou senha inválidos.' })
      await request.session.regenerate()
      request.session.adminId = user.id
      request.session.adminEmail = user.email
      request.session.csrfToken = token()
      return {
        user: { email: user.email },
        csrfToken: request.session.csrfToken,
      }
    }
  )
  app.post(
    '/api/auth/logout',
    { preHandler: requireAdmin },
    async (request, reply) => {
      if (
        !requireOrigin(request, reply, config) ||
        !requireCsrf(request, reply)
      )
        return
      await request.session.destroy()
      reply.clearCookie('sv_admin', {
        path: '/',
        httpOnly: true,
        sameSite: 'strict',
        secure: config.secureCookies,
      })
      return { ok: true }
    }
  )
}
