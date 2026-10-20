import type { Session } from 'fastify'
import type { SessionStore } from '@fastify/session'
import type { SqlDatabase } from '../db/sql.ts'

export function createSessionStore(db: SqlDatabase): SessionStore {
  const read = db.prepare('SELECT data FROM admin_sessions WHERE id = ? AND expires_at > ?')
  const put = db.prepare('INSERT INTO admin_sessions (id, data, expires_at) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET data=excluded.data, expires_at=excluded.expires_at')
  const remove = db.prepare('DELETE FROM admin_sessions WHERE id = ?')
  const purge = db.prepare('DELETE FROM admin_sessions WHERE expires_at <= ?')
  return {
    get(id, callback) {
      void (async () => {
        const row = await read.get(id, Date.now()) as { data: string } | undefined
        if (!row) { await remove.run(id); return null }
        return JSON.parse(row.data) as Session
      })().then(value => callback(null, value), error => callback(error))
    },
    set(id, session, callback) {
      void (async () => {
        const expires = session.cookie.expires ? new Date(session.cookie.expires).getTime() : Date.now() + 8 * 60 * 60 * 1000
        await purge.run(Date.now())
        await put.run(id, JSON.stringify(session), expires)
      })().then(() => callback(), error => callback(error))
    },
    destroy(id, callback) {
      void remove.run(id).then(() => callback(), error => callback(error))
    },
  }
}
