import { randomUUID } from 'node:crypto'
import { z } from 'zod'
import type { FastifyInstance } from 'fastify'
import type { SqlDatabase } from '../db/sql.ts'
import type { ServerConfig } from '../config.ts'
import { requireJsonMutation, requireOrigin } from '../auth/routes.ts'

const inputSchema = z
  .object({ email: z.string().trim().toLowerCase().max(254).email() })
  .strict()

export async function registerWaitlistRoutes(
  app: FastifyInstance,
  db: SqlDatabase,
  config: ServerConfig,
) {
  app.post(
    '/api/waitlist',
    { config: { rateLimit: { max: 5, timeWindow: '15 minutes' } } },
    async (request, reply) => {
      if (
        !requireOrigin(request, reply, config) ||
        !requireJsonMutation(request, reply)
      )
        return
      const parsed = inputSchema.safeParse(request.body)
      if (!parsed.success)
        return reply.code(400).send({ error: 'Informe um e-mail válido.' })
      // A unique normalized address is the idempotency boundary, including concurrent retries.
      await db
        .prepare(
          'INSERT INTO waitlist_entries (id, email, created_at) VALUES (?, ?, ?) ON CONFLICT (email) DO NOTHING',
        )
        .run(randomUUID(), parsed.data.email, new Date().toISOString())
      // Identical public receipts avoid revealing whether an address was already enrolled.
      return { registered: true }
    },
  )
}
