import { readFileSync } from 'node:fs'
import { generateSystemPrompt } from '@openuidev/lang-core'
import { createServer } from './app.ts'
import { loadConfig } from './config.ts'
import { createDatabase } from './db/database.ts'
import { MistralProvider } from './chat/mistral-provider.ts'
const config = loadConfig()
const spec = JSON.parse(
  readFileSync(new URL('../shared/openui-spec.json', import.meta.url), 'utf8')
)
const uiPrompt = generateSystemPrompt({
  library: spec,
  promptOptions: {
    toolCalls: false,
    bindings: false,
    builtinFunctions: false,
    inlineMode: false,
    editMode: false,
    additionalRules: [
      'Responda somente em OpenUI Lang, em português. Use um único Answer como root.',
      'Use apenas os componentes fornecidos. Textos curtos e concretos, com no máximo um card e cinco passos.',
      'Para dúvidas simples use Text. Use HowTo para funcionamento e BulletList para recursos. Ofereça ContactAction quando útil. Não invente métricas ou condições comerciais.',
    ],
  },
})
const database = createDatabase(config.databasePath)
const app = await createServer({
  config,
  database,
  chatProvider: new MistralProvider({
    apiKey: config.mistralApiKey,
    model: config.mistralModel,
    uiPrompt,
  }),
})
try {
  await app.listen({ host: '127.0.0.1', port: config.port })
  console.info(`Silent Voice API: http://127.0.0.1:${config.port}`)
  console.info(
    `Mistral: ${config.mistralApiKey ? 'configurado' : 'configure MISTRAL_API_KEY no .env para habilitar respostas'}`
  )
} catch {
  database.close()
  console.error(
    'Não foi possível iniciar a API. Verifique a configuração e a porta.'
  )
  process.exitCode = 1
}
for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.once(signal, () => {
    void app.close().finally(() => {
      database.close()
      process.exit(0)
    })
  })
}
