# @silent-voice/api

Fastify, Better Auth, PostgreSQL/Neon, CRM e proxy de chat Z.ai. Não depende de fontes React.

Configure `.env.example` em um `.env` privado deste workspace, com banco de desenvolvimento isolado. A inicialização aplica migrações sob lock e checksum. Comandos da raiz: `npm run dev:api`, `npm run build:api`, `npm run db:migrate`, `npm run admin:create -- --email administrador@exemplo.com`.

O processo publicado é API-only. `FRONTEND_PATH` é opcional e explícito para o preview combinado, nunca uma dependência implícita em `dist`. Leia [autenticação](../../docs/authentication.md) e [segurança](../../docs/security.md).
