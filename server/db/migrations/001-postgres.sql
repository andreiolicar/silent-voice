CREATE TABLE admin_users (
 id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE leads (
 rowid BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE,
 id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, objective TEXT NOT NULL,
 profile TEXT CHECK(profile IN ('self','family','professional','partner')), organization TEXT,
 status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','contacted','demo_scheduled','closed')),
 version INTEGER NOT NULL DEFAULT 1 CHECK(version > 0), created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 status_updated_by TEXT REFERENCES admin_users(id)
);
CREATE INDEX leads_email ON leads(email);
CREATE INDEX leads_created_at ON leads(created_at DESC, rowid DESC);
CREATE INDEX leads_status ON leads(status);
CREATE TABLE lead_notes (
 rowid BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE,
 id TEXT PRIMARY KEY, lead_id TEXT NOT NULL REFERENCES leads(id), text TEXT NOT NULL,
 author_id TEXT NOT NULL REFERENCES admin_users(id), created_at TEXT NOT NULL
);
CREATE INDEX lead_notes_lead ON lead_notes(lead_id, created_at, rowid);
CREATE TABLE lead_submissions (
 idempotency_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
 lead_id TEXT NOT NULL REFERENCES leads(id), created_at TEXT NOT NULL
);
CREATE TABLE admin_sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL, expires_at BIGINT NOT NULL);
CREATE INDEX admin_sessions_expiry ON admin_sessions(expires_at);
