import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { pathToFileURL } from "node:url";
import { createPostgresDatabase } from "./sql.ts";

/** Session-level migrations use the direct URL; lock and DDL share one transaction. */
export async function migratePostgres(url: string): Promise<void> {
  const db = createPostgresDatabase(url);
  try {
    await db
      .transaction(async () => {
        await db.lock("silent-voice-schema-migrations");
        await db.exec(
          "CREATE TABLE IF NOT EXISTS sv_schema_migrations (version INTEGER PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)",
        );
        const sql = await readFile(
          new URL("./migrations/001-postgres.sql", import.meta.url),
          "utf8",
        );
        const checksum = createHash("sha256").update(sql).digest("hex");
        const previous = (await db
          .prepare(
            "SELECT checksum FROM sv_schema_migrations WHERE version = ?",
          )
          .get(1)) as { checksum: string } | undefined;
        if (previous) {
          if (previous.checksum !== checksum)
            throw new Error("Applied migration checksum mismatch");
          return;
        }
        await db.exec(sql);
        await db
          .prepare("INSERT INTO sv_schema_migrations VALUES (?, ?, ?)")
          .run(1, checksum, new Date().toISOString());
      })
      .immediate();
  } finally {
    await db.close();
  }
}
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  const url = process.env.DATABASE_URL_UNPOOLED;
  if (!url) throw new Error("DATABASE_URL_UNPOOLED required for migrations");
  await migratePostgres(url)
    .then(() => console.info("PostgreSQL migrations: OK"))
    .catch(() => {
      console.error("PostgreSQL migrations failed");
      process.exitCode = 1;
    });
}
