# Silent Voice

Monorepo do produto: landing, administração, API, aplicativo e núcleo de reconhecimento. Este é o repositório principal: https://github.com/andreiolicar/silent-voice.

| Área | Caminho | Stack / responsabilidade |
| --- | --- | --- |
| Site | `apps/site` | React, Vite, Motion; landing e assistente comercial |
| Administração | `apps/admin` | React; CRM, login, recuperação e segurança |
| API | `apps/api` | Fastify, Better Auth, PostgreSQL/Neon e chatbot Z.ai |
| Aplicativo | `apps/mobile` | Expo SDK 57, React Native, autenticação e experiência do dispositivo |
| IA | `ai` | Núcleo de reconhecimento do João; código ainda não fornecido |
| Contratos | `packages/contracts` | DTOs do CRM/chat e especificação OpenUI, sem React |
| UI web | `packages/web-ui` | Botões, inputs, marca, tokens e entrada compartilhados |
| HTTP | `packages/http-client` | Política de disponibilidade usada pelos clientes web |

## Começar

Use Node 24 e npm 11. Instale **na raiz**, com o lockfile único:

```sh
npm ci
cp apps/api/.env.example apps/api/.env
# Configure um banco de desenvolvimento isolado e os segredos privados da API.
npm run dev
```

Site: http://127.0.0.1:5173 · administração: http://127.0.0.1:5173/admin · API: porta 3001. O comando inicia os três processos web; não inicia o mobile. Uma porta ocupada encerra os processos deste comando, sem encerrar servidores externos.

```sh
npm run dev:mobile
npm test
npm run typecheck
npm run build
npm run check:mobile
```

Não copie variáveis de produção para um servidor de teste. A API executa migrações na inicialização. Não há credenciais padrão. Leia [desenvolvimento](docs/development.md), [arquitetura](docs/architecture.md), [autenticação](docs/authentication.md), [segurança](docs/security.md), [deploy](docs/deployment.md) e [migração dos repositórios](docs/migration.md).

## Contribuir

Crie uma branch a partir de `main`, faça alterações pequenas e abra um PR. `CODEOWNERS` orienta revisão; não restringe acesso por pasta. João já tem permissão de escrita e começa por [ai/README.md](ai/README.md). Não versione chaves, dumps, gravações de usuários, datasets ou pesos de modelos.

O hardware continua atrás dos contratos do aplicativo. A migração não implementa um protocolo USB nem altera o reconhecimento. Componentes DOM ficam nos clientes web; o mobile preserva seu próprio design system.
