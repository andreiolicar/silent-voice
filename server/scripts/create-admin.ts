import { pathToFileURL } from 'node:url'
import { randomUUID } from 'node:crypto'
import { Pool } from 'pg'
import { z } from 'zod'
import { createAuth } from '../auth/better-auth.ts'
import { createAuthMailer } from '../auth/email.ts'
import { loadConfig } from '../config.ts'

/** Internal provisioning only. Passwords are set by their owner through Better Auth. */
export async function main(args = process.argv.slice(2)): Promise<void> {
  if (args.length !== 2 || args[0] !== '--email')
    throw new Error('Uso: npm run admin:create -- --email EMAIL')
  const email = z.email().parse(args[1]).toLowerCase()
  const config = loadConfig()
  if (!config.databaseUrl || !config.resendApiKey || !config.authSecret)
    throw new Error('Configure PostgreSQL, Better Auth e Resend antes de provisionar.')
  const url = new URL(config.databaseUrl)
  if (url.searchParams.get('sslmode') === 'require') url.searchParams.set('sslmode', 'verify-full')
  const database = new Pool({ connectionString: url.toString(), max: 1, connectionTimeoutMillis: 15000 })
  try {
    const existing = await database.query('SELECT id, role FROM auth_user WHERE email = $1', [email])
    if (existing.rows[0] && existing.rows[0].role !== 'admin')
      throw new Error('A conta existente não é administrativa. Promoção exige uma operação interna específica.')
    if (!existing.rows[0])
      await database.query(`INSERT INTO auth_user (id,name,email,"emailVerified","createdAt","updatedAt",role,banned,"twoFactorEnabled") VALUES ($1,$2,$3,FALSE,NOW(),NOW(),'admin',FALSE,FALSE)`, [randomUUID(), 'Administrador', email])
    const send = createAuthMailer(config.resendApiKey, config.authEmailFrom)
    const auth = createAuth(config, database, message => send({ ...message, kind: message.kind === 'reset' ? 'invite' : message.kind }))
    await auth.api.requestPasswordReset({ body: { email, redirectTo: `${config.authUrl || config.origin}/conta/redefinir-senha` } })
    process.stdout.write('Administrador provisionado. Instruções de definição de senha enviadas por e-mail.\n')
  } finally {
    await database.end()
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href)
  main().catch(() => {
    process.stderr.write('Não foi possível provisionar o administrador. Confira o e-mail, a configuração e o envio no Resend. Nenhuma senha é aceita por este comando.\n')
    process.exitCode = 1
  })
