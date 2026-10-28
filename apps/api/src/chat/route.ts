import type { OutgoingHttpHeaders } from 'node:http'
import type { FastifyInstance } from 'fastify'
import { z } from 'zod'
import type { ServerConfig } from '../config.ts'
import { isAllowedOrigin } from '../origin.ts'
import type { ChatProvider } from './provider.ts'
import { productKnowledge } from './knowledge.ts'
import type { ChatStreamEvent } from '@silent-voice/contracts/chat'
const schema = z
  .object({
    requestId: z
      .string()
      .min(1)
      .max(100)
      .regex(/^[\w-]+$/),
    messages: z
      .array(
        z
          .object({
            id: z.string().min(1).max(100),
            role: z.enum(['user', 'assistant']),
            content: z.string().min(1).max(8000),
          })
          .strict()
      )
      .min(1)
      .max(16),
  })
  .strict()
export async function registerChatRoute(
  app: FastifyInstance,
  config: ServerConfig,
  provider: ChatProvider
) {
  const byIp = new Map<string, number>()
  let total = 0
  app.post(
    '/api/chat',
    { config: { rateLimit: { max: 10, timeWindow: 60_000 } } },
    async (req, reply) => {
      if (!isAllowedOrigin(req.headers.origin, config))
        return reply.code(403).send({ error: 'Origem não permitida.' })
      const parsed = schema.safeParse(req.body)
      if (!parsed.success)
        return reply.code(400).send({ error: 'Mensagem inválida.' })
      const { messages, requestId } = parsed.data
      if (
        messages.at(-1)?.role !== 'user' ||
        messages.some(
          (m) =>
            !m.content.trim() || (m.role === 'user' && m.content.length > 2000)
        ) ||
        messages.reduce((sum, m) => sum + m.content.length, 0) > 16000
      )
        return reply.code(400).send({
          error: 'Conversa inválida ou longa demais. Inicie uma nova conversa.',
        })
      if ((byIp.get(req.ip) || 0) >= 2 || total >= 10)
        return reply
          .code(429)
          .send({ error: 'Aguarde a resposta em andamento e tente novamente.' })
      byIp.set(req.ip, (byIp.get(req.ip) || 0) + 1)
      total++
      const abort = new AbortController()
      const deadline = setTimeout(() => abort.abort(), config.chatTimeoutMs)
      let idle: ReturnType<typeof setTimeout> | undefined
      const resetIdle = () => {
        clearTimeout(idle)
        idle = setTimeout(() => abort.abort(), config.idleTimeoutMs)
      }
      const closed = () => {
        if (!reply.raw.writableEnded) abort.abort()
      }
      reply.raw.on('close', closed)
      reply.hijack()
      reply.raw.writeHead(200, {
        ...(reply.getHeaders() as OutgoingHttpHeaders),
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Accel-Buffering': 'no',
        'X-Content-Type-Options': 'nosniff',
      })
      const send = (event: ChatStreamEvent) => {
        if (!reply.raw.destroyed && !reply.raw.writableEnded)
          reply.raw.write(`data: ${JSON.stringify(event)}\n\n`)
      }
      let finalized = false
      let received = 0
      let iterator:
        AsyncIterator<import('./provider.ts').ProviderEvent> | undefined
      let rejectAbort: () => void = () => {}
      try {
        resetIdle()
        const aborted = new Promise<never>((_, reject) => {
          rejectAbort = () => reject(new Error('aborted'))
          abort.signal.addEventListener('abort', rejectAbort, { once: true })
        })
        iterator = provider
          .stream({
            messages: [
              { role: 'system', content: productKnowledge },
              ...messages.map(({ role, content }) => ({ role, content })),
            ],
            signal: abort.signal,
          })
          [Symbol.asyncIterator]()
        while (true) {
          const next = await Promise.race([iterator.next(), aborted])
          if (next.done) break
          resetIdle()
          const event = next.value
          if (event.type === 'delta' && event.text) {
            received += event.text.length
            if (received > 64000) throw new Error('output limit')
            send({ type: 'delta', requestId, text: event.text })
          } else if (event.type === 'done') {
            if (received === 0) throw new Error('empty completion')
            if (event.finishReason === 'other')
              throw new Error('unexpected termination')
            send({ type: 'done', requestId, finishReason: event.finishReason })
            finalized = true
            break
          }
        }
        if (!finalized)
          send({
            type: 'error',
            requestId,
            code: 'stream_interrupted',
            retryable: true,
          })
      } catch (error) {
        const rateLimited = error !== null && typeof error === 'object' &&
          (('statusCode' in error && error.statusCode === 429) || ('status' in error && error.status === 429))
        send({
          type: 'error',
          requestId,
          code: abort.signal.aborted ? 'timeout' : rateLimited ? 'provider_rate_limited' : 'provider_unavailable',
          retryable: true,
        })
      } finally {
        clearTimeout(deadline)
        clearTimeout(idle)
        abort.signal.removeEventListener('abort', rejectAbort)
        abort.abort()
        // Do not await an uncooperative upstream iterator during disconnect cleanup.
        if (iterator?.return) void iterator.return().catch(() => {})
        total--
        const count = (byIp.get(req.ip) || 1) - 1
        if (count) byIp.set(req.ip, count)
        else byIp.delete(req.ip)
        reply.raw.removeListener('close', closed)
        if (!reply.raw.writableEnded) reply.raw.end()
      }
    }
  )
}
