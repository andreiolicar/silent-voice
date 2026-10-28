# @silent-voice/mobile

Aplicativo React Native/Expo SDK 57, com onboarding, autenticação Better Auth, conexão/calibração ilustrativa e área interna. Preserva a arquitetura e o trabalho local importados; o transporte USB real ainda não foi implementado.

Instale **na raiz do monorepo** com `npm ci`. Não crie lockfile neste diretório.

```sh
npm run dev:mobile
npm test --workspace @silent-voice/mobile
npm run check:mobile
npm exec --workspace @silent-voice/mobile -- expo install --check
npm exec --workspace @silent-voice/mobile -- expo export --platform all
```

O backend padrão é `https://www.silentvoice.com.br`; configure `EXPO_PUBLIC_AUTH_URL` em `.env` local para um ambiente de teste. Não coloque segredos nessa variável. Leia [autenticação](../../docs/authentication.md), [arquitetura nativa](docs/architecture.md), [design system](docs/design-system.md) e [instruções da área](AGENTS.md).

Exportação não comprova execução em aparelho. A conexão física continua atrás do contrato `SilentVoiceDevice`; não há BLE/Wi-Fi ou driver USB novos nesta migração.
