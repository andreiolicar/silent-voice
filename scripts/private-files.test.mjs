import test from 'node:test'
import assert from 'node:assert/strict'
import { writeFile, unlink, mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import { randomUUID } from 'node:crypto'
import { createServer } from 'vite'

test('development server never serves private database or backup files, including /@fs paths', async () => {
  const marker = `qa-private-${randomUUID()}`
  const files = [
    `data/${marker}.sqlite`,
    `data/${marker}.sqlite-wal`,
    `data/${marker}.sqlite-shm`,
    `backups/${marker}.sqlite`,
    `backups/${marker}.dump`,
    `server/${marker}.txt`,
    `${marker}-configured`,
    `${marker}-configured-wal`,
    `.env.${marker}`,
    `${marker}.pem`,
  ]
  await mkdir('data', { recursive: true })
  await mkdir('backups', { recursive: true })
  for (const path of files)
    await writeFile(path, 'synthetic-private-fixture-no-personal-data')
  const previousDatabase = process.env.SQLITE_PATH
  process.env.SQLITE_PATH = resolve(`${marker}-configured`)
  const server = await createServer({
    root: process.cwd(),
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0, hmr: false },
  })
  try {
    await server.listen()
    const port = server.httpServer.address().port
    for (const path of files) {
      for (const urlPath of [`/${path}`, `/@fs${resolve(path)}`]) {
        const response = await fetch(`http://127.0.0.1:${port}${urlPath}`)
        assert.ok(
          response.status === 403 || response.status === 404,
          `${urlPath} must be private, got ${response.status}`
        )
      }
    }
    assert.equal((await fetch(`http://127.0.0.1:${port}/`)).status, 200)
    assert.equal(
      (await fetch(`http://127.0.0.1:${port}/assets/icone.svg`)).status,
      200
    )
  } finally {
    if (previousDatabase === undefined) delete process.env.SQLITE_PATH
    else process.env.SQLITE_PATH = previousDatabase
    await server.close()
    for (const path of files) await unlink(path).catch(() => {})
  }
})
