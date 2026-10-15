import { defineConfig, loadEnv, normalizePath } from 'vite'
import { resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'SQLITE_PATH')
  const database = normalizePath(
    resolve(
      process.env.SQLITE_PATH || env.SQLITE_PATH || 'data/silent-voice.sqlite'
    )
  )
  return {
    plugins: [react(), tailwindcss()],
    optimizeDeps: {
      include: [
        '@openuidev/react-lang',
        '@openuidev/react-ui/ThemeProvider',
        '@openuidev/react-ui/Card',
        '@openuidev/react-ui/Steps',
        '@openuidev/react-ui/Button',
        'zod/v4',
      ],
    },
    server: {
      proxy: { '/api': 'http://127.0.0.1:3001' },
      forwardConsole: false,
      fs: {
        // Preserve Vite 8 defaults and deny private application files on ordinary
        // URLs and /@fs/, including a configured database without an extension.
        deny: [
          '.env',
          '.env.*',
          '*.{crt,pem,key,p12,pfx,cer,der}',
          '.npmrc',
          '.yarnrc.yml',
          '**/.git/**',
          '**/data/**',
          '**/backups/**',
          '**/server/**',
          '**/docs/**',
          '**/.superpowers/**',
          '**/*.sqlite*',
          '**/*.sqlite3*',
          '**/*.db',
          '**/*.db-*',
          database,
          `${database}-*`,
        ],
      },
    },
  }
})
