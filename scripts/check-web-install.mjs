import { createRequire } from 'node:module'
import assert from 'node:assert/strict'

// The OpenUI generator runs under Node before Vite applies its React dedupe.
// Its hoisted CJS entry therefore needs the root build-time peer installation.
const site = createRequire(new URL('../apps/site/package.json', import.meta.url))
const openUi = createRequire(site.resolve('@openuidev/react-lang'))
assert.match(openUi('react/package.json').version, /^19\./)
for (const app of ['site', 'admin']) {
  const require = createRequire(new URL(`../apps/${app}/package.json`, import.meta.url))
  const declared = require('./package.json').dependencies.react
  assert.equal(require('react/package.json').version, declared, `${app} React version`)
  assert.equal(require('react-dom/package.json').version, declared, `${app} DOM version`)
}
console.log('Web application runtimes and OpenUI Node build-time peer: OK')
