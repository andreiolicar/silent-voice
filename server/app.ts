import Fastify from 'fastify'
import rateLimit from '@fastify/rate-limit'
import type { Database } from 'better-sqlite3'
import type { ServerConfig } from './config.ts'
import type { ChatProvider } from './chat/provider.ts'
import { registerChatRoute } from './chat/route.ts'
export async function createServer({
  config,
  chatProvider,
  database,
}: {
  config: ServerConfig
  chatProvider: ChatProvider
  database?: Database
}) {
  const app = Fastify({ logger: false, bodyLimit: 65536, trustProxy: false })
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
  app.get('/api/health', async () => ({ status: 'ok' }))
  await registerChatRoute(app, config, chatProvider)
  if (database) {
    const { registerDataRoutes } = await import('./leads/routes.ts')
    await registerDataRoutes(app, database, config)
  }
  return app
}
