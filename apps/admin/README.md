# @silent-voice/admin

Backoffice e páginas públicas de conta. URLs preservadas: `/admin/*` e `/conta/*`. Login, recuperação, 2FA e sessões usam o Better Auth da API; nenhum usuário ou segredo padrão.

Execute pela raiz com `npm run dev` e abra http://127.0.0.1:5173/admin. O servidor próprio usa 5174 e os assets de produção usam o prefixo `/admin/assets/`. Leia [autenticação](../../docs/authentication.md) e [deploy](../../docs/deployment.md).
