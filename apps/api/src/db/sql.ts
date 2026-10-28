import { AsyncLocalStorage } from "node:async_hooks";
import type Database from "better-sqlite3";
import { Pool } from "pg";
import type { PoolClient } from "pg";

type Result = { rows: unknown[]; changes: number };
type Statement = {
  get(...params: unknown[]): Promise<unknown>;
  all(...params: unknown[]): Promise<unknown[]>;
  run(...params: unknown[]): Promise<{ changes: number }>;
};
export interface SqlDatabase {
  readonly dialect: "postgres" | "sqlite";
  prepare(sql: string): Statement;
  exec(sql: string): Promise<void>;
  transaction<A extends unknown[], T>(
    work: (...args: A) => Promise<T>,
  ): { immediate(...args: A): Promise<T> };
  lock(key: string): Promise<void>;
  close(): Promise<void>;
}
export type DatabaseInput = Database.Database | SqlDatabase;

/** Translate application-owned bind markers only; values never enter SQL text. */
export function compilePostgres(
  sql: string,
  args: unknown[],
): { sql: string; values: unknown[] } {
  const values: unknown[] = [];
  let result = "",
    quoted = false,
    positional = 0;
  for (let index = 0; index < sql.length; index++) {
    const char = sql[index]!;
    if (char === "'") {
      result += char;
      if (quoted && sql[index + 1] === "'") {
        result += sql[++index];
        continue;
      }
      quoted = !quoted;
    } else if (!quoted && char === "?") {
      values.push(args[positional++]);
      result += `$${values.length}`;
    } else if (!quoted && char === "@" && /^\w/.test(sql[index + 1] || "")) {
      const name = sql.slice(index + 1).match(/^\w+/)![0];
      const named = args[0] as Record<string, unknown>;
      if (!named || !Object.hasOwn(named, name))
        throw new Error("Missing SQL binding");
      values.push(named[name]);
      result += `$${values.length}`;
      index += name.length;
    } else result += char;
  }
  return { sql: result, values };
}
function statements(
  execute: (sql: string, args: unknown[]) => Promise<Result>,
  sql: string,
): Statement {
  return {
    async get(...args) {
      return (await execute(sql, args)).rows[0];
    },
    async all(...args) {
      return (await execute(sql, args)).rows;
    },
    async run(...args) {
      return { changes: (await execute(sql, args)).changes };
    },
  };
}
const sqliteAdapters = new WeakMap<Database.Database, SqlDatabase>();
export function asSqlDatabase(input: DatabaseInput): SqlDatabase {
  if ("dialect" in input) return input;
  const raw: Database.Database = input;
  const cached = sqliteAdapters.get(raw);
  if (cached) return cached;
  // SQLite is retained for legacy import and fast regression fixtures only.
  // All adapter access is serialized so async transactions cannot interleave.
  const context = new AsyncLocalStorage<{ active: boolean }>();
  let pending = Promise.resolve();
  function serialize<T>(work: () => Promise<T>): Promise<T> {
    const next = pending.then(work, work);
    pending = next.then(
      () => undefined,
      () => undefined,
    );
    return next;
  }
  async function execute(sql: string, args: unknown[]): Promise<Result> {
    const run = async () => {
      const statement = raw.prepare(sql);
      if (statement.reader) return { rows: statement.all(...args), changes: 0 };
      return { rows: [], changes: statement.run(...args).changes };
    };
    const tx = context.getStore();
    if (tx) {
      if (!tx.active) throw new Error("Transaction ended");
      return run();
    }
    return serialize(run);
  }
  const adapter: SqlDatabase = {
    dialect: "sqlite",
    prepare: (sql) => statements(execute, sql),
    async exec(sql) {
      await serialize(async () => {
        raw.exec(sql);
      });
    },
    transaction(work) {
      return {
        immediate: (...args) =>
          serialize(async () => {
            const state = { active: true };
            raw.exec("BEGIN IMMEDIATE");
            try {
              const value = await context.run(state, () => work(...args));
              raw.exec("COMMIT");
              return value;
            } catch (error) {
              raw.exec("ROLLBACK");
              throw error;
            } finally {
              state.active = false;
            }
          }),
      };
    },
    async lock() {
      /* BEGIN IMMEDIATE serializes SQLite writers. */
    },
    async close() {
      await pending;
      if (raw.open) raw.close();
    },
  };
  sqliteAdapters.set(raw, adapter);
  return adapter;
}
export function createPostgresDatabase(connectionString: string): SqlDatabase {
  let secureUrl: URL;
  try {
    secureUrl = new URL(connectionString);
    if (!["postgres:", "postgresql:"].includes(secureUrl.protocol))
      throw new Error("Invalid protocol");
  } catch {
    throw new Error("Invalid PostgreSQL connection configuration");
  }
  if (secureUrl.searchParams.get("sslmode") === "require")
    secureUrl.searchParams.set("sslmode", "verify-full");
  const pool = new Pool({
    connectionString: secureUrl.toString(),
    max: 5,
    idleTimeoutMillis: 10_000,
    connectionTimeoutMillis: 15_000,
    statement_timeout: 20_000,
  });
  // An idle connection can be closed by a server restart. Surface no credentials.
  pool.on("error", () =>
    console.error("PostgreSQL: idle connection interrupted"),
  );
  const context = new AsyncLocalStorage<{
    client: PoolClient;
    active: boolean;
  }>();
  async function execute(sql: string, args: unknown[]): Promise<Result> {
    const tx = context.getStore();
    if (tx && !tx.active) throw new Error("Transaction ended");
    const bound = compilePostgres(sql, args);
    const result = await (tx?.client || pool).query(bound.sql, bound.values);
    return { rows: result.rows, changes: result.rowCount || 0 };
  }
  return {
    dialect: "postgres",
    prepare: (sql) => statements(execute, sql),
    async exec(sql) {
      await execute(sql, []);
    },
    transaction(work) {
      return {
        immediate: async (...args) => {
          if (context.getStore())
            throw new Error("Nested transactions are not supported");
          const client = await pool.connect();
          const state = { client, active: true };
          try {
            await client.query("BEGIN");
            const value = await context.run(state, () => work(...args));
            await client.query("COMMIT");
            return value;
          } catch (error) {
            await client.query("ROLLBACK").catch(() => {});
            throw error;
          } finally {
            state.active = false;
            client.release();
          }
        },
      };
    },
    async lock(key) {
      if (!context.getStore()?.active)
        throw new Error("Lock requires transaction");
      await execute("SELECT pg_advisory_xact_lock(hashtextextended(?, 0))", [
        key,
      ]);
    },
    async close() {
      await pool.end();
    },
  };
}
