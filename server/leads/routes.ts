import { createHash, randomUUID } from 'node:crypto'
import { z } from 'zod'
import type { FastifyInstance } from 'fastify'
import type Database from 'better-sqlite3'
import type { ServerConfig } from '../config.ts'
import type {
  AdminLead,
  LeadList,
  LeadNote,
  LeadStatus,
} from '../../shared/leads.ts'
import { leadStatuses } from '../../shared/leads.ts'
import {
  registerAuthRoutes,
  requireAdmin,
  requireCsrf,
  requireOrigin,
} from '../auth/routes.ts'

const inputSchema = z
  .object({
    name: z.string().trim().min(2).max(100),
    email: z.string().trim().toLowerCase().max(254).email(),
    objective: z.string().trim().min(10).max(1000),
    profile: z.enum(['self', 'family', 'professional', 'partner']).optional(),
    organization: z
      .string()
      .trim()
      .max(150)
      .optional()
      .transform((value) => value || undefined),
  })
  .strict()
const statusSchema = z
  .object({
    status: z.enum(leadStatuses),
    version: z.number().int().positive().max(Number.MAX_SAFE_INTEGER),
  })
  .strict()
const noteSchema = z
  .object({ text: z.string().trim().min(1).max(2000) })
  .strict()
const dateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .refine((value) => {
    const parsed = new Date(`${value}T00:00:00.000Z`)
    return (
      Number.isFinite(parsed.getTime()) &&
      parsed.toISOString().slice(0, 10) === value
    )
  })
const querySchema = z
  .object({
    q: z.string().trim().max(200).optional(),
    status: z.enum(leadStatuses).optional(),
    from: dateSchema.optional(),
    to: dateSchema.optional(),
    page: z
      .string()
      .regex(/^[1-9]\d*$/)
      .transform(Number)
      .refine((value) => Number.isSafeInteger(value) && value <= 1_000_000)
      .optional(),
  })
  .strict()
  .refine((value) => !value.from || !value.to || value.from <= value.to)

type LeadRow = {
  id: string
  name: string
  email: string
  objective: string
  profile: AdminLead['profile'] | null
  organization: string | null
  status: LeadStatus
  version: number
  created_at: string
  updated_at: string
  duplicate_email: number
}
function toLead(row: LeadRow): AdminLead {
  return {
    id: row.id,
    name: row.name,
    email: row.email,
    objective: row.objective,
    ...(row.profile ? { profile: row.profile } : {}),
    ...(row.organization ? { organization: row.organization } : {}),
    status: row.status,
    version: row.version,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    duplicateEmail: Boolean(row.duplicate_email),
  }
}
const selectLead = `SELECT l.*, EXISTS(SELECT 1 FROM leads duplicate WHERE duplicate.email = l.email AND duplicate.id != l.id) AS duplicate_email FROM leads l`

export async function registerDataRoutes(
  app: FastifyInstance,
  db: Database.Database,
  config: ServerConfig
): Promise<void> {
  await registerAuthRoutes(app, db, config)
  const findSubmission = db.prepare(
    'SELECT fingerprint, lead_id, created_at FROM lead_submissions WHERE idempotency_key = ?'
  )
  const insertLead = db.prepare(
    'INSERT INTO leads (id, name, email, objective, profile, organization, created_at, updated_at) VALUES (@id, @name, @email, @objective, @profile, @organization, @createdAt, @createdAt)'
  )
  const insertSubmission = db.prepare(
    'INSERT INTO lead_submissions (idempotency_key, fingerprint, lead_id, created_at) VALUES (?, ?, ?, ?)'
  )
  const saveLead = db.transaction(
    (key: string, fingerprint: string, data: z.infer<typeof inputSchema>) => {
      const existing = findSubmission.get(key) as
        { fingerprint: string; lead_id: string; created_at: string } | undefined
      if (existing)
        return existing.fingerprint === fingerprint
          ? {
              status: 200,
              receipt: { id: existing.lead_id, createdAt: existing.created_at },
            }
          : { status: 422 }
      const receipt = { id: randomUUID(), createdAt: new Date().toISOString() }
      insertLead.run({
        ...data,
        ...receipt,
        profile: data.profile || null,
        organization: data.organization || null,
      })
      insertSubmission.run(key, fingerprint, receipt.id, receipt.createdAt)
      return { status: 201, receipt }
    }
  )
  app.post(
    '/api/leads',
    { config: { rateLimit: { max: 5, timeWindow: '15 minutes' } } },
    async (request, reply) => {
      if (!requireOrigin(request, reply, config)) return
      const key = z.uuid().safeParse(request.headers['idempotency-key'])
      const parsed = inputSchema.safeParse(request.body)
      if (!key.success || !parsed.success)
        return reply.code(400).send({ error: 'Dados inválidos.' })
      const fingerprint = createHash('sha256')
        .update(JSON.stringify(parsed.data))
        .digest('hex')
      const result = saveLead.immediate(
        key.data.toLowerCase(),
        fingerprint,
        parsed.data
      )
      if (result.status === 422)
        return reply
          .code(422)
          .send({ error: 'Esta solicitação não pode ser reutilizada.' })
      return reply.code(result.status).send(result.receipt)
    }
  )

  const findLead = db.prepare(`${selectLead} WHERE l.id = ?`)
  const notes = db.prepare(
    'SELECT n.id, n.text, u.email author, n.created_at createdAt FROM lead_notes n JOIN admin_users u ON n.author_id = u.id WHERE n.lead_id = ? ORDER BY n.created_at, n.rowid'
  )
  const changeStatus = db.prepare(
    'UPDATE leads SET status = ?, version = version + 1, updated_at = ?, status_updated_by = ? WHERE id = ? AND version = ?'
  )
  const insertNote = db.prepare(
    'INSERT INTO lead_notes (id, lead_id, text, author_id, created_at) VALUES (?, ?, ?, ?, ?)'
  )
  app.get(
    '/api/admin/leads',
    { preHandler: requireAdmin },
    async (request, reply) => {
      const parsed = querySchema.safeParse(request.query)
      if (!parsed.success)
        return reply.code(400).send({ error: 'Filtros inválidos.' })
      const query = parsed.data
      const page = query.page || 1
      const conditions: string[] = []
      const params: (string | number)[] = []
      if (query.q) {
        conditions.push(
          "(l.name LIKE ? ESCAPE '\\' OR l.email LIKE ? ESCAPE '\\' OR l.objective LIKE ? ESCAPE '\\')"
        )
        const pattern = `%${query.q.replace(/[\\%_]/g, '\\$&')}%`
        params.push(pattern, pattern, pattern)
      }
      if (query.status) {
        conditions.push('l.status = ?')
        params.push(query.status)
      }
      if (query.from) {
        conditions.push('l.created_at >= ?')
        params.push(`${query.from}T00:00:00.000Z`)
      }
      if (query.to) {
        conditions.push('l.created_at <= ?')
        params.push(`${query.to}T23:59:59.999Z`)
      }
      const where = conditions.length
        ? ` WHERE ${conditions.join(' AND ')}`
        : ''
      const rows = db
        .prepare(
          `${selectLead}${where} ORDER BY l.created_at DESC, l.rowid DESC LIMIT 25 OFFSET ?`
        )
        .all(...params, (page - 1) * 25) as LeadRow[]
      const total = (
        db
          .prepare(`SELECT count(*) total FROM leads l${where}`)
          .get(...params) as { total: number }
      ).total
      const counts: LeadList['counts'] = {
        new: 0,
        contacted: 0,
        demo_scheduled: 0,
        closed: 0,
      }
      for (const row of db
        .prepare('SELECT status, count(*) total FROM leads GROUP BY status')
        .all() as { status: LeadStatus; total: number }[])
        counts[row.status] = row.total
      return { items: rows.map(toLead), total, page, counts } satisfies LeadList
    }
  )
  app.get<{ Params: { id: string } }>(
    '/api/admin/leads/:id',
    { preHandler: requireAdmin },
    async (request, reply) => {
      const row = findLead.get(request.params.id) as LeadRow | undefined
      if (!row)
        return reply.code(404).send({ error: 'Registro não encontrado.' })
      return { lead: toLead(row), notes: notes.all(row.id) as LeadNote[] }
    }
  )
  app.patch<{ Params: { id: string } }>(
    '/api/admin/leads/:id',
    { preHandler: requireAdmin },
    async (request, reply) => {
      if (
        !requireOrigin(request, reply, config) ||
        !requireCsrf(request, reply)
      )
        return
      const parsed = statusSchema.safeParse(request.body)
      if (!parsed.success)
        return reply.code(400).send({ error: 'Dados inválidos.' })
      const result = db
        .transaction(() => {
          const existing = findLead.get(request.params.id) as
            LeadRow | undefined
          if (!existing) return { status: 404 as const }
          if (
            !changeStatus.run(
              parsed.data.status,
              new Date().toISOString(),
              request.session.adminId!,
              existing.id,
              parsed.data.version
            ).changes
          )
            return { status: 409 as const }
          return {
            status: 200 as const,
            lead: toLead(findLead.get(existing.id) as LeadRow),
          }
        })
        .immediate()
      if (result.status !== 200)
        return reply
          .code(result.status)
          .send({
            error:
              result.status === 409
                ? 'O registro foi alterado. Atualize os dados.'
                : 'Registro não encontrado.',
          })
      return result.lead
    }
  )
  app.post<{ Params: { id: string } }>(
    '/api/admin/leads/:id/notes',
    { preHandler: requireAdmin },
    async (request, reply) => {
      if (
        !requireOrigin(request, reply, config) ||
        !requireCsrf(request, reply)
      )
        return
      const parsed = noteSchema.safeParse(request.body)
      if (!parsed.success)
        return reply.code(400).send({ error: 'Dados inválidos.' })
      if (!findLead.get(request.params.id))
        return reply.code(404).send({ error: 'Registro não encontrado.' })
      const note: LeadNote = {
        id: randomUUID(),
        text: parsed.data.text,
        author: request.session.adminEmail!,
        createdAt: new Date().toISOString(),
      }
      insertNote.run(
        note.id,
        request.params.id,
        note.text,
        request.session.adminId!,
        note.createdAt
      )
      return reply.code(201).send(note)
    }
  )
}
