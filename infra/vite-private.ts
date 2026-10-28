/** Shared by the two dev servers, which may resolve files across workspaces. */
export const privateFiles = [
  '**/.env', '**/.env.*', '*.{crt,pem,key,p12,pfx,cer,der}',
  '**/.git/**', '**/.npmrc', '**/.yarnrc.yml', '**/.neon/**',
  '**/apps/api/**', '**/server/**', '**/data/**', '**/backups/**',
  '**/ai/**', '**/docs/**', '**/.superpowers/**',
  '**/*.sqlite*', '**/*.db', '**/*.db-*',
]
