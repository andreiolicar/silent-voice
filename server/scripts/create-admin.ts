import { pathToFileURL } from 'node:url'
import { createPostgresDatabase } from '../db/sql.ts'
import { provisionAdmin } from '../auth/password.ts'

/** Read from a private TTY only: never accept credentials as arguments or env. */
export function promptPassword(label: string): Promise<string> {
  if (!process.stdin.isTTY || !process.stderr.isTTY)
    throw new Error('Execute este comando em um terminal privado interativo.')
  return new Promise((resolve, reject) => {
    const input = process.stdin
    const wasRaw = input.isRaw
    let value = ''
    process.stderr.write(label)
    input.setRawMode(true)
    input.resume()
    const finish = (error?: Error) => {
      input.off('data', onData)
      input.setRawMode(wasRaw)
      input.pause()
      process.stderr.write('\n')
      if (error) reject(error)
      else resolve(value)
    }
    const onData = (chunk: Buffer) => {
      for (const character of chunk.toString('utf8')) {
        if (character === '\u0003' || character === '\u0004') {
          finish(new Error('Operação cancelada.'))
          return
        }
        if (character === '\r' || character === '\n') {
          finish()
          return
        }
        if (character === '\u007f' || character === '\b')
          value = Array.from(value).slice(0, -1).join('')
        else if (character >= ' ' && value.length < 257) value += character
      }
    }
    input.on('data', onData)
  })
}
export async function main(args = process.argv.slice(2)): Promise<void> {
  if (args.length !== 2 || args[0] !== '--email' || !args[1])
    throw new Error(
      'Uso: npm run admin:create -- --email EMAIL. A senha será solicitada em terminal privado.'
    )
  const password = await promptPassword('Senha (12 a 256 caracteres): ')
  const confirmation = await promptPassword('Confirme a senha: ')
  if (password !== confirmation) throw new Error('As senhas não coincidem.')
  if (!process.env.DATABASE_URL) throw new Error('DATABASE_URL required')
  const db = createPostgresDatabase(process.env.DATABASE_URL)
  try {
    await provisionAdmin(db, args[1], password)
    process.stdout.write('Administrador criado.\n')
  } finally {
    await db.close()
  }
}
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  main().catch(() => {
    process.stderr.write(
      'Não foi possível criar o administrador. Verifique o e-mail, a senha, o terminal privado e se o usuário já existe.\n'
    )
    process.exitCode = 1
  })
}
