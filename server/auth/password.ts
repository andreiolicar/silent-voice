import { randomBytes, randomUUID, scrypt, timingSafeEqual } from 'node:crypto'
import type Database from 'better-sqlite3'
import { z } from 'zod'

const params = { N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 }
function derive(password: string, salt: string): Promise<Buffer> {
  return new Promise((resolve, reject) =>
    scrypt(password, salt, 64, params, (error, key) =>
      error ? reject(error) : resolve(key)
    )
  )
}
export async function hashPassword(password: string): Promise<string> {
  if (password.length < 12 || password.length > 256)
    throw new Error('A senha deve ter de 12 a 256 caracteres.')
  const salt = randomBytes(32).toString('hex')
  return `scrypt$32768$8$1$${salt}$${(await derive(password, salt)).toString('hex')}`
}
export async function verifyPassword(
  password: string,
  hash: string
): Promise<boolean> {
  const parts = hash.split('$')
  const valid =
    parts.length === 6 &&
    parts.slice(0, 4).join('$') === 'scrypt$32768$8$1' &&
    /^[a-f0-9]{64}$/.test(parts[4]!) &&
    /^[a-f0-9]{128}$/.test(parts[5]!)
  // Unknown users do the same expensive operation as known users.
  const key = await derive(password, valid ? parts[4]! : '0'.repeat(64))
  const expected = Buffer.from(valid ? parts[5]! : '0'.repeat(128), 'hex')
  return timingSafeEqual(key, expected) && valid
}
export async function provisionAdmin(
  db: Database.Database,
  email: string,
  password: string
): Promise<{ id: string; email: string }> {
  const normalized = z.email().max(254).parse(email.trim().toLowerCase())
  const passwordHash = await hashPassword(password)
  const id = randomUUID()
  db.prepare(
    'INSERT INTO admin_users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)'
  ).run(id, normalized, passwordHash, new Date().toISOString())
  return { id, email: normalized }
}
