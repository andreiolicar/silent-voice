import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createRequire } from 'node:module'

test('the mobile app, native runtime and renderer resolve one React instance without changing SDK versions', () => {
  const mobile = createRequire(new URL('../apps/mobile/package.json', import.meta.url))
  const react = mobile.resolve('react')
  assert.equal(mobile('react/package.json').version, '19.2.3')
  assert.equal(mobile('react-native/package.json').version, '0.86.3')
  for (const name of ['react-native/package.json', 'react-test-renderer/package.json'])
    assert.equal(createRequire(mobile.resolve(name)).resolve('react'), react, `${name} must share the mobile dispatcher`)
})

test('published web build preserves separate admin assets and account entry at the original URLs', async t => {
  const { assembleWeb, documentForPath } = await import('../infra/build-web.mjs')
  const root = await mkdtemp(join(tmpdir(), 'sv-web-build-'))
  t.after(() => rm(root, { recursive: true, force: true }))
  for (const app of ['site', 'admin']) {
    await mkdir(join(root, app, 'assets'), { recursive: true })
    await writeFile(join(root, app, 'index.html'), `<html>${app}</html>`)
    await writeFile(join(root, app, 'assets', 'main.js'), app)
  }
  const outDir = join(root, 'published')
  await assembleWeb({ siteDir: join(root, 'site'), adminDir: join(root, 'admin'), outDir })
  assert.equal(await readFile(join(outDir, 'assets/main.js'), 'utf8'), 'site')
  assert.equal(await readFile(join(outDir, 'admin/assets/main.js'), 'utf8'), 'admin')
  for (const path of ['/', '/produto']) assert.equal(documentForPath(path), 'index.html')
  for (const path of ['/admin', '/admin/login', '/admin/cadastros', '/conta/redefinir-senha?token=fixture']) {
    assert.equal(documentForPath(path), 'admin/index.html')
    assert.equal(await readFile(join(outDir, documentForPath(path)), 'utf8'), '<html>admin</html>')
  }
})

test('an incomplete build never removes the previous published output or source directories', async t => {
  const { assembleWeb } = await import('../infra/build-web.mjs')
  const root = await mkdtemp(join(tmpdir(), 'sv-web-failed-build-'))
  t.after(() => rm(root, { recursive: true, force: true }))
  const outDir = join(root, 'published')
  await mkdir(outDir); await writeFile(join(outDir, 'index.html'), 'previous')
  await assert.rejects(assembleWeb({ siteDir: join(root, 'missing'), adminDir: join(root, 'missing-admin'), outDir }))
  assert.equal(await readFile(join(outDir, 'index.html'), 'utf8'), 'previous')
  await assert.rejects(assembleWeb({ siteDir: outDir, adminDir: outDir, outDir: root }), /overlap|source|unsafe/i)
  assert.equal(await readFile(join(outDir, 'index.html'), 'utf8'), 'previous')
})
