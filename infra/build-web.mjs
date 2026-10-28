import { cp, mkdir, mkdtemp, readFile, rename, rm } from 'node:fs/promises'
import { dirname, join, parse, resolve, sep } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
export { documentForPath } from '@silent-voice/contracts/web'

export async function assembleWeb({ siteDir, adminDir, outDir }) {
  const output = resolve(outDir)
  const sources = [resolve(siteDir), resolve(adminDir)]
  if (output === parse(output).root || sources.some(source => source === output || source.startsWith(output + sep) || output.startsWith(source + sep)))
    throw new Error('Unsafe overlapping source and output directories')
  // Validate both complete builds before touching the previous output.
  await Promise.all(sources.map(source => readFile(join(source, 'index.html'))))
  await mkdir(dirname(output), { recursive: true })
  const staging = await mkdtemp(join(dirname(output), '.web-build-'))
  try {
    await cp(sources[0], staging, { recursive: true })
    await cp(sources[1], join(staging, 'admin'), { recursive: true })
    await rm(output, { recursive: true, force: true })
    await rename(staging, output)
  } catch (error) {
    await rm(staging, { recursive: true, force: true })
    throw error
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const root = fileURLToPath(new URL('../', import.meta.url))
  await assembleWeb({ siteDir: join(root, 'apps/site/dist'), adminDir: join(root, 'apps/admin/dist'), outDir: join(root, 'dist') })
  console.log('Published frontend assembled: landing + /admin + /conta')
}
