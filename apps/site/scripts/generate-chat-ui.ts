import { writeFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
// OpenUI 0.18.1 component subpaths publish extensionless ESM internals.
// tsx's require transform selects their working CJS builds without importing
// the large react-ui root barrel or duplicating the frontend registry.
const require = createRequire(import.meta.url)
const { silentVoiceLibrary } =
  require('../src/features/chatbot/response-library.tsx') as typeof import('../src/features/chatbot/response-library')
await writeFile(
  new URL(import.meta.resolve('@silent-voice/contracts/openui-spec.json')),
  `${JSON.stringify(silentVoiceLibrary.toSpec(), null, 2)}\n`
)
