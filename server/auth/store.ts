import type { Session } from 'fastify'
import type { SessionStore } from '@fastify/session'
import type Database from 'better-sqlite3'

export function createSessionStore(db: Database.Database): SessionStore {
  const read = db.prepare(
    'SELECT data FROM admin_sessions WHERE id = ? AND expires_at > ?'
  )
  const put = db.prepare(
    'INSERT INTO admin_sessions (id, data, expires_at) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET data=excluded.data, expires_at=excluded.expires_at'
  )
  const remove = db.prepare('DELETE FROM admin_sessions WHERE id = ?')
  const purge = db.prepare('DELETE FROM admin_sessions WHERE expires_at <= ?')
  // No timers or memory store: expiration is checked on every read and expired rows
  // are removed during writes, so app.close has no background resource to stop.
  return {
    get(id, callback) {
      try {
        const row = read.get(id, Date.now()) as { data: string } | undefined
        if (!row) {
          remove.run(id)
          callback(null, null)
          return
        }
        callback(null, JSON.parse(row.data) as Session)
      } catch (error) {
        callback(error)
      }
    },
    set(id, session, callback) {
      try {
        const expires = session.cookie.expires
          ? new Date(session.cookie.expires).getTime()
          : Date.now() + 8 * 60 * 60 * 1000
        purge.run(Date.now())
        put.run(id, JSON.stringify(session), expires)
        callback()
      } catch (error) {
        callback(error)
      }
    },
    destroy(id, callback) {
      try {
        remove.run(id)
        callback()
      } catch (error) {
        callback(error)
      }
    },
  }
}
