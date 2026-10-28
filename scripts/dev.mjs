import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../', import.meta.url))
const sitePort = Number(process.env.SITE_PORT || 5173)
const adminPort = Number(process.env.ADMIN_PORT || 5174)
const apiPort = Number(process.env.PORT || 3001)
const origin = `http://127.0.0.1:${sitePort}`
const env = { ...process.env, NODE_ENV: 'development', PORT: String(apiPort), APP_ORIGIN: origin, BETTER_AUTH_URL: origin, ADDITIONAL_APP_ORIGINS: `http://127.0.0.1:${adminPort}`, VITE_API_PROXY: `http://127.0.0.1:${apiPort}`, ADMIN_DEV_URL: `http://127.0.0.1:${adminPort}` }
const children = []
let closing = false
function stop() {
  if (closing) return
  closing = true
  for (const child of children) child.kill('SIGTERM')
}
function start(name, args, cwd) {
  const child = spawn(process.execPath, args, { cwd, env, stdio: 'inherit' })
  children.push(child)
  child.on('error', error => { console.error(`${name}: ${error.message}`); process.exitCode = 1; stop() })
  child.on('exit', code => { if (!closing) { process.exitCode = code || 0; stop() } })
}
for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, stop)
start('api', ['--env-file-if-exists=.env', '--experimental-strip-types', 'src/index.ts'], resolve(root, 'apps/api'))
for (const [name, port] of [['site', sitePort], ['admin', adminPort]]) {
  const cwd = resolve(root, 'apps', name)
  const require = createRequire(resolve(cwd, 'package.json'))
  const vite = resolve(dirname(require.resolve('vite/package.json')), 'bin/vite.js')
  start(name, [vite, '--host', '127.0.0.1', '--port', String(port), '--strictPort'], cwd)
}
console.log(`Silent Voice: ${origin} · admin ${origin}/admin · API :${apiPort}`)
