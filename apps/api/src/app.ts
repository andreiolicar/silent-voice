import Fastify from 'fastify'
import rateLimit from '@fastify/rate-limit'
import { isAllowedOrigin } from './origin.ts'
import { asSqlDatabase } from './db/sql.ts'
import type { DatabaseInput } from './db/sql.ts'
import type { ServerConfig } from './config.ts'
import type { ChatProvider } from './chat/provider.ts'
import { registerAuthRoutes } from './auth/routes.ts'
import type { SilentVoiceAuth } from './auth/better-auth.ts'
import { documentForPath } from '@silent-voice/contracts/web'
import { registerChatRoute } from './chat/route.ts'
export async function createServer({
  config,
  chatProvider,
  database,
  auth,
}: {
  config: ServerConfig
  chatProvider: ChatProvider
  database?: DatabaseInput
  auth?: SilentVoiceAuth
}) {
  const app = Fastify({ logger: false, bodyLimit: 65536, trustProxy: config.trustProxy ? (_address, hop) => hop === 0 : false })
  app.addHook('onRequest', async (request, reply) => {
    if (isAllowedOrigin(request.headers.origin, config)) {
      reply.header('Access-Control-Allow-Origin', request.headers.origin!)
      reply.header('Vary', 'Origin')
      reply.header('Access-Control-Allow-Credentials', 'true')
    }
    if (request.method === 'OPTIONS' && request.url.startsWith('/api/')) {
      if (!isAllowedOrigin(request.headers.origin, config)) return reply.code(403).send({error:'Solicitação não permitida.'})
      reply.header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
      reply.header('Access-Control-Allow-Headers', 'Content-Type, X-CSRF-Token, Idempotency-Key')
      return reply.code(204).send()
    }
  })
  await app.register(rateLimit, { global: false, skipOnError: false })
  app.addHook('onSend', async (_req, reply) => {
    reply.header('X-Content-Type-Options', 'nosniff')
    reply.header('Cache-Control', 'no-store')
    reply.header('Referrer-Policy', 'same-origin')
  })
  app.setErrorHandler((error, _req, reply) => {
    const status = (error as { statusCode?: number }).statusCode || 500
    reply
      .code(status)
      .send({
        error:
          status === 429
            ? 'Muitas tentativas. Tente novamente mais tarde.'
            : status === 400
              ? 'Dados inválidos.'
              : 'Não foi possível concluir a solicitação.',
      })
  })
  app.get('/api/health', async () => {
    if (database) await asSqlDatabase(database).prepare('SELECT 1').get()
    return { status: 'ok' }
  })
  await registerAuthRoutes(app, auth || null, config)
  await registerChatRoute(app, config, chatProvider)
  if (database) {
    const { registerDataRoutes } = await import('./leads/routes.ts')
    await registerDataRoutes(app, asSqlDatabase(database), config)
  }
  if (config.frontendPath) {
    const { default: staticFiles } = await import('@fastify/static')
    const { resolve } = await import('node:path')
    await app.register(staticFiles, { root: resolve(config.frontendPath, 'assets'), prefix: '/assets/' })
    await app.register(staticFiles, { root: resolve(config.frontendPath, 'admin/assets'), prefix: '/admin/assets/', decorateReply: false })
    app.get('/intro-bootstrap.js', (_request, reply) => reply.sendFile('intro-bootstrap.js', config.frontendPath!))
    app.get('/', (_request, reply) => reply.sendFile('index.html', config.frontendPath!))
    app.setNotFoundHandler((request, reply) => {
      if (['GET', 'HEAD'].includes(request.method) && /^\/(?:admin|conta)(?:\/|$)/.test(request.url.split('?')[0]!)) return reply.sendFile(documentForPath(request.url), config.frontendPath!)
      return reply.code(404).send({error:'Não encontrado.'})
    })
  }
  return app
}
