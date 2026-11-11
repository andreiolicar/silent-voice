CREATE TABLE waitlist_entries (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);
CREATE INDEX waitlist_entries_created_at ON waitlist_entries(created_at DESC);
