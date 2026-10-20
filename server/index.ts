import { readFileSync } from "node:fs";
import { generateSystemPrompt } from "@openuidev/lang-core";
import { createServer } from "./app.ts";
import { loadConfig } from "./config.ts";
import { createPostgresDatabase } from "./db/sql.ts";
import { migratePostgres } from "./db/migrate.ts";
import { ZaiProvider } from "./chat/zai-provider.ts";
async function start() {
  let database: ReturnType<typeof createPostgresDatabase> | undefined;
  let app: Awaited<ReturnType<typeof createServer>> | undefined;
  try {
    const config = loadConfig();
    const spec = JSON.parse(
      readFileSync(
        new URL("../shared/openui-spec.json", import.meta.url),
        "utf8",
      ),
    );
    const uiPrompt = generateSystemPrompt({
      library: spec,
      promptOptions: {
        toolCalls: false,
        bindings: false,
        builtinFunctions: false,
        inlineMode: false,
        editMode: false,
        additionalRules: [
          "Responda somente em OpenUI Lang, em português. Use um único Answer como root.",
          "Use apenas os componentes fornecidos. Textos curtos e concretos, com no máximo um card e cinco passos.",
          "Para dúvidas simples use Text. Use HowTo para funcionamento e BulletList para recursos. Ofereça ContactAction quando útil. Não invente métricas ou condições comerciais.",
        ],
      },
    });
    if (!config.databaseUrl || !config.directDatabaseUrl)
      throw new Error("Configure DATABASE_URL and DATABASE_URL_UNPOOLED");
    await migratePostgres(config.directDatabaseUrl);
    database = createPostgresDatabase(config.databaseUrl);
    app = await createServer({
      config,
      database,
      chatProvider: new ZaiProvider({
        apiKey: config.zaiApiKey,
        model: config.zaiModel,
        uiPrompt,
      }),
    });
    await app.listen({ host: config.host || "0.0.0.0", port: config.port });
    console.info(`Silent Voice API: http://127.0.0.1:${config.port}`);
    console.info(
      `GLM-4.5-Flash: ${config.zaiApiKey ? "configurado" : "configure ZAI_API_KEY no .env para habilitar respostas"}`,
    );

    for (const signal of ["SIGINT", "SIGTERM"] as const) {
      process.once(signal, () => {
        void (async () => {
          try {
            await app?.close();
          } finally {
            await database?.close();
          }
        })().then(
          () => process.exit(0),
          () => process.exit(1),
        );
      });
    }
  } catch {
    await app?.close().catch(() => {});
    await database?.close().catch(() => {});
    console.error(
      "Não foi possível iniciar a API. Verifique banco, configuração e porta.",
    );
    process.exitCode = 1;
  }
}
await start();
