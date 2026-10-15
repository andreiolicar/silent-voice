import Database from 'better-sqlite3'
import { mkdirSync } from 'node:fs'
import { dirname } from 'node:path'

const migration = `
CREATE TABLE leads (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, objective TEXT NOT NULL,
 profile TEXT CHECK(profile IN ('self','family','professional','partner')), organization TEXT,
 status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','contacted','demo_scheduled','closed')),
 version INTEGER NOT NULL DEFAULT 1 CHECK(version > 0), created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX leads_email ON leads(email);
CREATE INDEX leads_created_at ON leads(created_at DESC);
CREATE INDEX leads_status ON leads(status);
CREATE TABLE admin_users (
 id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE lead_notes (
 id TEXT PRIMARY KEY, lead_id TEXT NOT NULL REFERENCES leads(id), text TEXT NOT NULL,
 author_id TEXT NOT NULL REFERENCES admin_users(id), created_at TEXT NOT NULL
);
CREATE INDEX lead_notes_lead ON lead_notes(lead_id, created_at);
CREATE TABLE lead_submissions (
 idempotency_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
 lead_id TEXT NOT NULL REFERENCES leads(id), created_at TEXT NOT NULL
);
CREATE TABLE admin_sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL, expires_at INTEGER NOT NULL);
CREATE INDEX admin_sessions_expiry ON admin_sessions(expires_at);
`

export function createDatabase(path: string): Database.Database {
  if (path !== ':memory:')
    mkdirSync(dirname(path), { recursive: true, mode: 0o700 })
  const db = new Database(path)
  try {
    db.pragma('journal_mode = WAL')
    db.pragma('foreign_keys = ON')
    db.pragma('busy_timeout = 5000')
    db.transaction(() => {
      db.exec(
        'CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)'
      )
      if (
        !db
          .prepare('SELECT version FROM schema_migrations WHERE version = 1')
          .get()
      ) {
        db.exec(migration)
        db.prepare(
          'INSERT INTO schema_migrations (version, applied_at) VALUES (1, ?)'
        ).run(new Date().toISOString())
      }
      if (
        !db
          .prepare('SELECT version FROM schema_migrations WHERE version = 2')
          .get()
      ) {
        db.exec(
          'ALTER TABLE leads ADD COLUMN status_updated_by TEXT REFERENCES admin_users(id)'
        )
        db.prepare(
          'INSERT INTO schema_migrations (version, applied_at) VALUES (2, ?)'
        ).run(new Date().toISOString())
      }
    }).immediate()
    return db
  } catch (error) {
    db.close()
    throw error
  }
}
