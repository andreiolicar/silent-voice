# Desenvolvimento

Requisitos: Node 24 e npm 11, conforme `.node-version` e `package.json`. Execute todos os comandos a partir da raiz.

- `npm ci`: instalação completa, incluindo mobile.
- `npm run dev`: API + site + admin, sem mobile. Use `SITE_PORT`, `ADMIN_PORT` e `PORT` se já houver servidores ativos.
- `npm run dev:site`, `dev:admin`, `dev:api`: execução individual. Admin direto usa porta 5174; prefira a origem única `5173/admin` pelo proxy da landing.
- `npm run dev:mobile`: Expo no workspace mobile.
- `npm run build`: builds web combinados e typecheck da API.
- `npm run preview`: preview integrado em 4173, usando **o banco de desenvolvimento da API**.
- `npm test`, `npm run typecheck`, `npm run check:mobile`: verificações.

Copie `apps/api/.env.example` para `apps/api/.env`. Configure um PostgreSQL isolado em `DATABASE_URL` e a conexão direta em `DATABASE_URL_UNPOOLED`. O startup aplica migrações transacionais. Configure Better Auth e Resend para testar os fluxos de conta. Sem `ZAI_API_KEY`, o chat informa indisponibilidade; leads e administração não dependem da IA.

O mobile aponta por padrão para `https://www.silentvoice.com.br`. Para testar um backend isolado, use `EXPO_PUBLIC_AUTH_URL` em `apps/mobile/.env`; em aparelho físico, loopback não aponta para o computador. Essa URL é pública, não uma chave.

## Testes PostgreSQL reais

Os testes unitários não precisam de segredos. Os testes externos são opt-in e manipulam apenas o banco isolado informado. Nunca forneça a URL de produção:

```sh
TEST_DATABASE_URL_FILE=/caminho/privado/url-isolada node --experimental-strip-types --test apps/api/tests/postgres.integration.test.mjs
AUTH_TEST_DATABASE_URL_FILE=/caminho/privado/url-isolada node --experimental-strip-types --test apps/api/tests/unified-auth-migration.test.mjs
```

Os arquivos devem conter apenas a URL privada. Não os versione. Fixtures sintéticas não pertencem à produção.

## Mobile

```sh
npm exec --workspace @silent-voice/mobile -- expo install --check
npm exec --workspace @silent-voice/mobile -- expo-doctor
npm exec --workspace @silent-voice/mobile -- expo export --platform all
```

Consulte a [documentação SDK 57](https://docs.expo.dev/versions/v57.0.0/) e o [guia de monorepos](https://docs.expo.dev/guides/monorepos/) antes de alterar resolução ou módulos nativos. As versões anteriores à migração foram mantidas; eventuais atualizações de patch exigem um ciclo próprio de validação.
