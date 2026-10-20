# Assistente Silent Voice e backoffice

## Execução local

Requer Node.js 24 LTS e npm. `npm ci` instala o driver SQLite nativo; em uma plataforma sem binário pré-compilado, o npm precisará das ferramentas de compilação da plataforma.

1. Copie `.env.example` para `.env`. Defina `ZAI_API_KEY` no arquivo local, nunca no chat, em código ou com prefixo `VITE_`. O modelo é configurável por `ZAI_MODEL` (inicial: `glm-4.5-flash`).
2. Defina `SESSION_SECRET` com ao menos 32 caracteres aleatórios antes de qualquer publicação. O modo local usa um fallback apenas para desenvolvimento se esse campo estiver vazio.
3. Execute em dois terminais:

```sh
npm run dev:api
npm run dev
```

A landing está em http://127.0.0.1:5173 e a API local em http://127.0.0.1:3001. O Vite encaminha `/api`. `APP_ORIGIN` define a origem permitida, incluindo protocolo e porta. No desenvolvimento local, `localhost` e `127.0.0.1` são aceitos como alternativas somente no mesmo protocolo e porta configurados. Em produção, e para domínios que não sejam loopback, a origem deve corresponder exatamente à configurada. O processo da API precisa ser reiniciado após alterar o `.env`.

Sem chave Z.ai, o assistente informa indisponibilidade real; o formulário de interesse e o backoffice continuam funcionando. Não há respostas simuladas habilitadas no produto. A qualidade, a latência e o acesso ao modelo precisam ser validados com a conta configurada.

Um `429` da Z.ai é repassado como `provider_rate_limited`, sem retry automático ou exposição da resposta privada do provedor. Use uma **Standard API Key** da API comum, não uma chave de Coding Plan ou BigModel. O modelo padrão `glm-4.5-flash` consta como gratuito na [tabela oficial](https://docs.z.ai/guides/overview/pricing); confirme os limites da conta no [painel da Z.ai](https://z.ai/manage-apikey/rate-limits). Não há fallback para outro modelo nem ativação de faturamento. Alterar `ZAI_MODEL` manualmente pode selecionar um modelo pago.

## Administrador

Não existe usuário ou senha padrão. Em terminal privado interativo:

```sh
npm run admin:create -- --email seu-email@exemplo.com
```

O comando solicita senha e confirmação sem mostrar os caracteres. A senha deve ter de 12 a 256 caracteres; não é aceita por argumento ou variável de ambiente. Entre em http://127.0.0.1:5173/admin. A rota não aparece na navegação pública.

O painel permite pesquisar, filtrar por status/data, paginar, consultar dados completos, adicionar notas e atualizar o status. “Demonstração combinada” é uma marcação manual, sem reserva de agenda ou envio de e-mail. Conflitos de edição retornam 409 e preservam o rascunho da nota. O rascunho permanece apenas na memória da aba; logout explícito ou recarregamento o descarta.

Sessões duram oito horas, ficam no PostgreSQL e usam cookie HttpOnly/SameSite Strict. O login troca ID e token CSRF; logout invalida a sessão no servidor. Senhas são armazenadas com scrypt e salt aleatório.

## Respostas visuais

OpenUI usa `@openuidev/react-lang@1.0.1` e componentes oficiais de `@openuidev/react-ui@0.18.1`. O painel segue Inter, `#1AA99B`, `#051B34` e os tokens da landing. Não usa OpenUI Gateway ou assinatura do serviço.

A biblioteca controlada está em `src/features/chatbot/response-library.tsx`: Answer, Text, HowTo, BulletList e ContactAction. Não aceita HTML, Markdown, URLs, formulários gerados, ferramentas ou ações arbitrárias. ContactAction abre somente o formulário local. A renderização é protegida contra respostas inválidas e componentes parciais. O CSS/tema fica limitado ao assistente. O inspector automático de desenvolvimento do OpenUI1.0.1 é desativado antes do lazy load, evitando UI extra e carregamento de scripts do CDN; o guard específico da versão precisa ser revisto ao atualizar o pacote.

`npm run generate:chat` gera `shared/openui-spec.json` a partir da biblioteca real. A API deriva desse contrato as instruções da linguagem visual. Regere após alterar componentes; o prebuild faz isso automaticamente. O gerador usa o caminho CJS dos componentes publicados para contornar os imports ESM sem extensão do pacote, enquanto o browser importa componentes individuais para reduzir o bundle.

O proxy usa `fetch` nativo do Node na API padrão `https://api.z.ai/api/paas/v4/chat/completions`, com `glm-4.5-flash`, streaming SSE, thinking desativado e até 2.048 tokens de saída. Não há SDK extra ou retry automático. O adapter preserva os papéis da conversa, envia fatos e contrato OpenUI como instrução de sistema e repassa somente texto visível; raciocínio e ferramentas ficam excluídos. Valida limites de frames, UTF-8, término explícito e cancelamento do leitor. EOF ou `[DONE]` sem `finish_reason` não são convertidos em sucesso.

O contexto admite 16 mensagens e 16 mil caracteres; cada mensagem do visitante tem até 2.000 caracteres. O servidor controla modelo, prompt e fatos; o cliente não pode enviar instruções de sistema. Não são prometidos preço, disponibilidade, latência, precisão, transcrição em tempo real ou resultado clínico sem confirmação.

## Fluxos e dados

### Interface do assistente

O painel usa os mesmos tokens de fonte, cor e borda da landing e da administração, com cantos de 24 px, controles em pílula e foco turquesa discreto. Os ajustes ficam isolados em `#silent-voice-chat`; os botões públicos da landing não são alterados. O launcher mantém a marca branca e sua entrada em bolha.

`ChatButton` concentra ações e tamanhos do chat; `ChatComposer` controla o campo de mensagem, que cresce até quatro linhas e se reajusta quando a largura muda. A saudação e as sugestões aparecem apenas antes da primeira mensagem. O cabeçalho mantém somente minimizar; o formulário é acessado por “Solicitar demonstração” ou pela ação local das respostas OpenUI, com retorno à conversa. O formulário mostra nome, e-mail e objetivo primeiro; perfil e organização ficam em “Informações opcionais”, preservando os valores ao recolher. `chat-response.css` adapta os componentes oficiais do OpenUI à mesma hierarquia visual, sem mudar o contrato das respostas.

O launcher aparece depois da abertura da landing, sem abrir o painel automaticamente. No primeiro clique, o módulo é carregado sem container intermediário; falhas reais ainda exibem a alternativa de contato. Minimizar preserva conversa e envio. Mudar de rota desmonta o assistente, cancela a geração e ignora respostas obsoletas. Enter envia, Shift+Enter quebra a linha e composição IME não envia acidentalmente. O hover não desloca os controles; as marcas do cabeçalho e do launcher compartilham a mesma proporção interna.

O chat envia texto à API Z.ai; não persiste transcrições completas no banco ou no localStorage. Campos do formulário não são enviados automaticamente ao modelo. Os [termos para API](https://docs.z.ai/legal-agreement/terms-of-use) informam que o conteúdo de desenvolvedores não é usado para aprimorar os serviços sem concordância explícita; isso não é uma promessa de retenção zero. Revisar o aviso de privacidade antes de publicar e não enviar dados clínicos.

Contatos são registrados por `POST /api/leads`, independentemente da IA. Nome, e-mail e objetivo são obrigatórios; perfil e organização são opcionais. A confirmação exige recibo após commit PostgreSQL. Timeout de 15 segundos mantém payload/chave imutáveis; tentar novamente recupera o mesmo recibo e não duplica o registro. O mesmo e-mail pode ter solicitações distintas. Registros incluem status, versão, datas e notas com autor.

Limites locais: chat 10 mensagens/minuto/IP, duas gerações/IP e dez globais; leads e login cinco tentativas/15 minutos/IP. Requisições têm body máximo de 64 KiB. A geração encerra após 45 segundos ou 15 segundos sem progresso, propagando o sinal de cancelamento à requisição HTTP e ao leitor de streaming, sem retry automático. O cancelamento local não garante interrupção de processamento ou cobrança de uma requisição já aceita pela Z.ai. Logs não registram texto, contatos, cookies, senhas ou chaves.

## Banco e backup

O runtime usa PostgreSQL no Neon: DATABASE_URL com pool para consultas e DATABASE_URL_UNPOOLED para migrações. Nenhum arquivo SQLite é usado pelo servidor publicado. Migrações versionadas são transacionais e verificadas por checksum; sessões, recibos e cadastros persistem no banco externo.

Execute npm run db:migrate antes de validar uma nova versão. A inicialização também executa as migrações sob advisory lock. Para importar um snapshot SQLite privado consistente, use npm run db:import:sqlite -- caminho-do-backup.sqlite. A importação preserva IDs, hashes de senha e datas; conflitos revertem a transação, sem sobrescrever dados. Sessões antigas não são importadas.

O comando db:backup mantém apenas a função de snapshot do SQLite legado. Para o PostgreSQL, utilize pg_dump com conexão direta e destino privado, ou os recursos de recuperação do Neon conforme a retenção disponível no plano. Nunca publique dumps ou URLs de conexão.

## Validação

```sh
npm test
npm run typecheck
npm run build
npm audit
```

A suíte mantém os testes anteriores e acrescenta streaming UTF-8/cancelamento, limites/concorrência, OpenUI seguro, lifecycle do chat, recibo idempotente/retry, banco/backup e autenticação/admin. Fixtures com respostas e contatos fictícios existem somente nos testes. Consulte `docs/reference/chatbot/validation.md` localmente para capturas e limites da conferência manual.

## Publicação futura

Produção: frontend estático no Render, API Node no Render Free e PostgreSQL no Neon Free. Segredos pertencem apenas ao ambiente do backend. O processo escuta em 0.0.0.0 e PORT; confia apenas no proxy imediatamente anterior, usa cookies Secure/HttpOnly/SameSite Strict e exige origem exata para mutações. /api/health consulta o banco. Instâncias gratuitas podem suspender por inatividade; os dados permanecem no Neon.
