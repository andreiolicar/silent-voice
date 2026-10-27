# Silent Voice — design aprovado do monorepo

O proprietário aprovou em 27/10/2026 reunir os três repositórios em `andreiolicar/silent-voice`, incluindo a landing, com deploys independentes. A alternativa de manter a landing separada foi recusada.

## Estrutura e limites

- `apps/site`: landing, animações e assistente comercial.
- `apps/admin`: backoffice, login e páginas públicas de conta.
- `apps/api`: Fastify, Better Auth, PostgreSQL/Neon, CRM e chatbot.
- `apps/mobile`: Expo57 atual e todo o working tree local existente.
- `packages/contracts`: contratos chat/CRM e especificação OpenUI; sem React ou segredos.
- `packages/web-ui`: controles e estilos realmente usados pelos dois frontends web, sem importação pelo mobile.
- `assets/brand`: marca original preservada.
- `ai`: núcleo de reconhecimento do João, independente do chatbot e do npm. Ainda não há código de IA fornecido; não inventar uma implementação ou linguagem.
- `docs` e `infra`: documentação atual e deploy.

Usar npm workspaces; preservar versões atuais, incluindo React19.3 web e React19.2.3/RN0.86.3/Expo57 mobile. Não adicionar orquestrador, serviços pagos, integração USB/driver, BLE ou novos modelos. Componentes DOM não são compartilhados com React Native.

## Preservação e produção

Importar históricos sem squash ou reescrita. Acrescentar snapshot do trabalho local mobile no monorepo, sem modificar os clones de origem. Remover PDFs obsoletos da árvore atual; continuarão recuperáveis pelo histórico Git. Conservar logos, SQL existente, dados, credenciais e identidade Better Auth. Segredos/backups/datasets/artefatos pesados fora do Git comum.

Manter domínio e rotas `/api/*`, `/admin/*` e `/conta/*`, banco Neon e os dois serviços Render gratuitos. Site/admin são builds separados combinados em um único diretório estático. Alterar origem dos deploys somente após testes/build/revisão. Rollback usa origem/revisão anteriores, sem restaurar ou apagar o banco.

## Colaboração e aceite

João já tem escrita no repositório: atribuir `ai/` no CODEOWNERS e documentar branches/PRs e instalação por área. Não impor bloqueios ao bootstrap nem expandir permissões. Arquivar fontes reversivelmente depois do corte validado, mantendo clones locais.

Aceite: instalação reproduzível na raiz; testes/types/builds web/API; testes/lint/types/formatação/exports mobile; histórico e snapshot auditáveis; HTML/rotas corretos em produção; sessão/2FA preservados; documentação atual. Exportação não prova execução em aparelho; registrar limitações reais.
