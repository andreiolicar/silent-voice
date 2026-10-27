import Database from "better-sqlite3";
import { pathToFileURL } from "node:url";
import type { SqlDatabase } from "../db/sql.ts";
import { createPostgresDatabase } from "../db/sql.ts";
import { migratePostgres } from "../db/migrate.ts";

const tables = [
  {
    name: "admin_users",
    key: "id",
    columns: ["id", "email", "password_hash", "created_at"],
  },
  {
    name: "leads",
    key: "id",
    columns: [
      "id",
      "name",
      "email",
      "objective",
      "profile",
      "organization",
      "status",
      "version",
      "created_at",
      "updated_at",
      "status_updated_by",
    ],
  },
  {
    name: "lead_notes",
    key: "id",
    columns: ["id", "lead_id", "text", "author_id", "created_at"],
  },
  {
    name: "lead_submissions",
    key: "idempotency_key",
    columns: ["idempotency_key", "fingerprint", "lead_id", "created_at"],
  },
] as const;
/** Import a consistent private SQLite backup. Conflicts abort; no data is overwritten. */
export async function importSqlite(
  target: SqlDatabase,
  sourcePath: string,
): Promise<Record<string, number>> {
  const source = new Database(sourcePath, {
    readonly: true,
    fileMustExist: true,
  });
  try {
    if (source.pragma("integrity_check", { simple: true }) !== "ok")
      throw new Error("Invalid source backup");
    const counts: Record<string, number> = {};
    await target
      .transaction(async () => {
        await target.lock("silent-voice-sqlite-import");
        for (const table of tables) {
          const columns = table.columns.join(", ");
          const rows = source
            .prepare(`SELECT ${columns} FROM ${table.name} ORDER BY rowid`)
            .all() as Record<string, unknown>[];
          let inserted = 0;
          for (const row of rows) {
            const existing = (await target
              .prepare(
                `SELECT ${columns} FROM ${table.name} WHERE ${table.key} = ?`,
              )
              .get(row[table.key])) as Record<string, unknown> | undefined;
            if (existing) {
              if (table.columns.some((key) => existing[key] !== row[key]))
                throw new Error(`Import conflict in ${table.name}`);
              continue;
            }
            await target
              .prepare(
                `INSERT INTO ${table.name} (${columns}) VALUES (${table.columns.map(() => "?").join(", ")})`,
              )
              .run(...table.columns.map((key) => row[key]));
            inserted++;
          }
          counts[table.name] = inserted;
        }
      })
      .immediate();
    return counts;
  } finally {
    source.close();
  }
}
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  let target: SqlDatabase | undefined;
  try {
    if (
      process.argv.length !== 3 ||
      !process.env.DATABASE_URL ||
      !process.env.DATABASE_URL_UNPOOLED
    )
      throw new Error("Invalid import configuration");
    await migratePostgres(process.env.DATABASE_URL_UNPOOLED);
    target = createPostgresDatabase(process.env.DATABASE_URL);
    console.info(
      "Import counts:",
      await importSqlite(target, process.argv[2]!),
    );
  } catch {
    console.error("Import aborted; transaction rolled back. Source preserved.");
    process.exitCode = 1;
  } finally {
    await target?.close();
  }
}
