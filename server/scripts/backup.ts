import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { createDatabase } from '../db/database.ts'
import { backupDatabase } from '../db/backup.ts'

export async function main(args = process.argv.slice(2)): Promise<void> {
  const source = process.env.SQLITE_PATH || 'data/silent-voice.sqlite'
  const destination = args[0]
  if (
    args.length !== 1 ||
    !destination ||
    !existsSync(source) ||
    existsSync(destination) ||
    resolve(source) === resolve(destination)
  )
    throw new Error('Forneça um destino novo e uma base existente.')
  const db = createDatabase(source)
  try {
    await backupDatabase(db, destination)
    process.stdout.write('Backup concluído.\n')
  } finally {
    db.close()
  }
}
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  main().catch(() => {
    process.stderr.write(
      'Não foi possível concluir o backup. Verifique a origem e use um destino novo.\n'
    )
    process.exitCode = 1
  })
}
