import type Database from 'better-sqlite3'

/** The SQLite backup API includes committed WAL pages in a consistent snapshot. */
export async function backupDatabase(
  db: Database.Database,
  destination: string
): Promise<void> {
  await db.backup(destination)
}
