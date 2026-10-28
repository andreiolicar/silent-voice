import { access } from 'node:fs/promises'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'

const root = fileURLToPath(new URL('../', import.meta.url))
await access(join(root, 'dist/admin/index.html'))
const port = process.env.PORT || '4173'
const origin = `http://127.0.0.1:${port}`
const child = spawn(process.execPath, ['--env-file-if-exists=.env', '--experimental-strip-types', 'src/index.ts'], {
  cwd: join(root, 'apps/api'), stdio: 'inherit',
  env: { ...process.env, NODE_ENV: 'development', PORT: port, FRONTEND_PATH: join(root, 'dist'), APP_ORIGIN: origin, BETTER_AUTH_URL: origin },
})
for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, () => child.kill('SIGTERM'))
child.on('exit', code => { process.exitCode = code || 0 })
console.log(`Combined local preview: ${origin} (uses the API development database)`)
