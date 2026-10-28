# Publicação e operação

Destino canônico: `andreiolicar/silent-voice`, branch `main`. Permanecem os dois serviços existentes na conta `contatosilentvoice@gmail.com`, workspace `My Workspace`:

| Serviço | ID | Configuração |
| --- | --- | --- |
| Frontend | `srv-dbbrls0473hc73da6r10` | Static Site, publica `dist` |
| API | `srv-dbbsfnd9fdbs73a3pm10` | Node, Oregon, Free, health `/api/health` |

Banco PostgreSQL externo no Neon. Nenhum serviço adicional ou upgrade de plano faz parte desta migração. `infra/render.yaml` documenta a configuração dos serviços existentes; não é instrução para criar serviços duplicados.

## Build e start

Frontend:

```sh
npm run ci:web
npm run build:web
```

API:

```sh
npm run ci:api
npm run build:api
npm run start --workspace @silent-voice/api
```

Raiz do serviço vazia (raiz do repositório), Node 24, `SKIP_INSTALL_DEPS=true` para não executar uma instalação automática completa antes da selecionada. `.npmrc` e lockfile são compartilhados. `ci:web` inclui as ferramentas da raiz porque o gerador OpenUI executa CJS antes do Vite e precisa do peer React. Isso não instala Expo/React Native. A CI também exercita instalações reduzidas em runners independentes, sem poder resolver dependências de um checkout pai. O comando build da API valida os tipos; Node 24 executa o TypeScript suportado por strip-types.

## Rotas e domínios

O domínio continua `https://www.silentvoice.com.br`; apex redireciona para www. Não há alteração DNS. Os assets da landing ficam em `/assets`; os administrativos em `/admin/assets`. As regras em `infra/routes.json` mantêm `/api/*` para a API, `/admin` e `/conta` para `admin/index.html`, e a landing como último fallback. Arquivos reais devem ser servidos antes do fallback.

## Ambiente e identidade

Preserve todos os valores existentes, sobretudo `BETTER_AUTH_SECRET`, URLs, banco, remetente Resend e chaves. Não gere um novo segredo ao trocar de repositório: ele protege sessões e os segredos de 2FA. Não copie segredos para o frontend. A API não precisa de `FRONTEND_PATH` no Render.

## Corte e retorno

1. Validar instalação limpa, testes, builds e ensaio PostgreSQL isolado.
2. Salvar privadamente configuração/rotas dos serviços e referência do deploy anterior.
3. Integrar o monorepo sem reescrever históricos. Desligar temporariamente auto-deploy e alterar repositório/branch/comandos dos serviços existentes.
4. Publicar a revisão escolhida, aplicar as regras do static site e conferir HTML, JS/CSS, API, sessão e 2FA preservados. Restaurar auto-deploy após o aceite.
5. Arquivar os repositórios de origem reversivelmente somente após as verificações.

Se falhar, restaure a configuração do serviço anterior: repositório `silent-voice-site`, branch `deploy/static-frontend`, revisão `f6d4c9c714a182e3873f60ddc405f9d0fdb8cf4d`, comandos e regras salvos. Publique frontend e API compatíveis. **Não restaure um dump sobre produção:** o banco permanece atual e esta migração não muda o SQL. Reative o repositório antigo se necessário para o rollback.

Validação não deve consumir tentativas de login do proprietário. Use testes de autenticação em banco isolado; em produção, confira health, respostas públicas/401 e metadados de sessão sem divulgar cookies ou credenciais.
