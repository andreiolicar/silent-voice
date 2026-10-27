import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify'
import { fromNodeHeaders } from 'better-auth/node'
import type { ServerConfig } from '../config.ts'
import type { SilentVoiceAuth } from './better-auth.ts'
import { isAllowedOrigin } from '../origin.ts'
import { isIP } from 'node:net'

type AuthSession = NonNullable<Awaited<ReturnType<SilentVoiceAuth['api']['getSession']>>>
declare module 'fastify' {
  interface FastifyInstance { auth: SilentVoiceAuth | null }
  interface FastifyRequest { authSession?: AuthSession }
}
export function requireOrigin(request: FastifyRequest, reply: FastifyReply, config: ServerConfig): boolean {
  if (!isAllowedOrigin(request.headers.origin, config)) {
    reply.code(403).send({error:'Solicitação não permitida.'}); return false
  }
  return true
}
/** Application mutations remain same-origin JSON; auth endpoints use Better Auth's CSRF checks. */
export function requireJsonMutation(request: FastifyRequest, reply: FastifyReply): boolean {
  if (!request.headers['content-type']?.toLowerCase().startsWith('application/json')) {
    reply.code(415).send({error:'Envie os dados em JSON.'}); return false
  }
  return true
}
export async function requireAdmin(request: FastifyRequest, reply: FastifyReply): Promise<void> {
  const auth = request.server.auth
  const result = auth ? await auth.api.getSession({
    headers: fromNodeHeaders(request.headers),
    returnHeaders: true,
  }) : null
  // Daily session renewal and stale-cookie cleanup must reach the browser,
  // including when the application subsequently denies this authenticated user.
  const cookies = result?.headers.getSetCookie() ?? []
  if (cookies.length) {
    const existing = reply.getHeader('set-cookie')
    const previous = existing === undefined ? [] : Array.isArray(existing) ? existing : [String(existing)]
    reply.header('Set-Cookie', [...previous, ...cookies])
  }
  const session = result?.response ?? null
  if (!session) { reply.code(401).send({error:'Autenticação necessária.'}); return }
  if (session.user.role !== 'admin' || !session.user.emailVerified) {
    reply.code(403).send({error:'Acesso não permitido.',code:'FORBIDDEN'}); return
  }
  if (!session.user.twoFactorEnabled) {
    reply.code(403).send({error:'Configure a autenticação em duas etapas.',code:'MFA_SETUP_REQUIRED'}); return
  }
  request.authSession = session
}
export async function registerAuthRoutes(app: FastifyInstance, auth: SilentVoiceAuth | null, config: ServerConfig) {
  app.decorate('auth', auth)
  if (!auth) return
  app.route({
    method: ['GET','POST'], url:'/api/auth/*',
    async handler(request, reply) {
      const url = new URL(request.url, auth.options.baseURL as string)
      const headers = fromNodeHeaders(request.headers)
      // On Render, its Cloudflare edge overwrites the configured visitor header.
      // Elsewhere retain Fastify's bounded proxy policy. Never take the arbitrary
      // leftmost forwarded token, or pass a multi-hop chain to the SDK limiter.
      const edgeAddress = config.trustedClientIpHeader ? request.headers[config.trustedClientIpHeader] : undefined
      const clientAddress = typeof edgeAddress === 'string' && isIP(edgeAddress) ? edgeAddress : request.ip
      headers.set('x-forwarded-for', clientAddress)
      const response = await auth.handler(new Request(url, {
        method:request.method, headers,
        ...(request.body ? {body:JSON.stringify(request.body)} : {}),
      }))
      reply.code(response.status)
      for (const [key,value] of response.headers) if(key.toLowerCase() !== 'set-cookie') reply.header(key,value)
      const cookies=response.headers.getSetCookie()
      if(cookies.length) reply.header('Set-Cookie',cookies)
      const body = response.body ? Buffer.from(await response.arrayBuffer()) : null
      const retryAfter = Number(response.headers.get('x-retry-after') || response.headers.get('retry-after'))
      if (response.status === 429 && Number.isFinite(retryAfter) && retryAfter > 0 && body) {
        reply.header('Retry-After', String(Math.ceil(retryAfter)))
        reply.removeHeader('Content-Length')
        return reply.send({ ...JSON.parse(body.toString()), retryAfterSeconds: Math.ceil(retryAfter) })
      }
      return reply.send(body)
    },
  })
}
