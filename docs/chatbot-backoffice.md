# Assistente Silent Voice e backoffice

## Execução local

Requer Node.js 24 LTS e npm. `npm ci` instala o driver SQLite nativo; em uma plataforma sem binário pré-compilado, o npm precisará das ferramentas de compilação da plataforma.

1. Copie `.env.example` para `.env`. Defina `MISTRAL_API_KEY` no arquivo local, nunca no chat, em código ou com prefixo `VITE_`. O modelo é configurável por `MISTRAL_MODEL` (inicial: `mistral-small-2603`).
2. Defina `SESSION_SECRET` com ao menos 32 caracteres aleatórios antes de qualquer publicação. O modo local usa um fallback apenas para desenvolvimento se esse campo estiver vazio.
3. Execute em dois terminais:

```sh
npm run dev:api
npm run dev
```

A landing está em http://127.0.0.1:5173 e a API local em http://127.0.0.1:3001. O Vite encaminha `/api`. `APP_ORIGIN` define a origem permitida, incluindo protocolo e porta. No desenvolvimento local, `localhost` e `127.0.0.1` são aceitos como alternativas somente no mesmo protocolo e porta configurados. Em produção, e para domínios que não sejam loopback, a origem deve corresponder exatamente à configurada. O processo da API precisa ser reiniciado após alterar o `.env`.

Sem chave Mistral, o assistente informa indisponibilidade real; o formulário de interesse e o backoffice continuam funcionando. Não há respostas simuladas habilitadas no produto. A qualidade, a latência e o acesso ao modelo precisam ser validados com a conta configurada.

## Administrador

Não existe usuário ou senha padrão. Em terminal privado interativo:

```sh
npm run admin:create -- --email seu-email@exemplo.com
```

O comando solicita senha e confirmação sem mostrar os caracteres. A senha deve ter de 12 a 256 caracteres; não é aceita por argumento ou variável de ambiente. Entre em http://127.0.0.1:5173/admin. A rota não aparece na navegação pública.

O painel permite pesquisar, filtrar por status/data, paginar, consultar dados completos, adicionar notas e atualizar o status. “Demonstração combinada” é uma marcação manual, sem reserva de agenda ou envio de e-mail. Conflitos de edição retornam 409 e preservam o rascunho da nota. O rascunho permanece apenas na memória da aba; logout explícito ou recarregamento o descarta.

Sessões duram oito horas, ficam em SQLite e usam cookie HttpOnly/SameSite Strict. O login troca ID e token CSRF; logout invalida a sessão no servidor. Senhas são armazenadas com scrypt e salt aleatório.

## Respostas visuais

OpenUI usa `@openuidev/react-lang@1.0.1` e componentes oficiais de `@openuidev/react-ui@0.18.1`. O painel segue Inter, `#1AA99B`, `#051B34` e os tokens da landing. Não usa OpenUI Gateway ou assinatura do serviço.

A biblioteca controlada está em `src/features/chatbot/response-library.tsx`: Answer, Text, HowTo, BulletList e ContactAction. Não aceita HTML, Markdown, URLs, formulários gerados, ferramentas ou ações arbitrárias. ContactAction abre somente o formulário local. A renderização é protegida contra respostas inválidas e componentes parciais. O CSS/tema fica limitado ao assistente. O inspector automático de desenvolvimento do OpenUI1.0.1 é desativado antes do lazy load, evitando UI extra e carregamento de scripts do CDN; o guard específico da versão precisa ser revisto ao atualizar o pacote.

`npm run generate:chat` gera `shared/openui-spec.json` a partir da biblioteca real. A API deriva desse contrato as instruções da linguagem visual. Regere após alterar componentes; o prebuild faz isso automaticamente. O gerador usa o caminho CJS dos componentes publicados para contornar os imports ESM sem extensão do pacote, enquanto o browser importa componentes individuais para reduzir o bundle.

O proxy usa o SDK oficial Mistral, temperatura 0,2, até 1.400 tokens, 16 mensagens e 16 mil caracteres de contexto. Mensagens do visitante têm até 2.000 caracteres. O servidor controla modelo, prompt e fatos; o cliente não pode enviar instruções de sistema. Câmera/leitura labial e EMG com três eletrodos trabalham juntos; o microfone fornece contexto e o alto-falante do dispositivo reproduz áudio. Não são prometidos preço, disponibilidade, latência, precisão ou resultado clínico sem confirmação.

## Fluxos e dados

### Interface do assistente

O painel usa os mesmos tokens de fonte, cor e borda da landing e da administração, com cantos de 24 px, controles em pílula e foco turquesa discreto. Os ajustes ficam isolados em `#silent-voice-chat`; os botões públicos da landing não são alterados. O launcher mantém a marca branca e sua entrada em bolha.

`ChatButton` concentra ações e tamanhos do chat; `ChatComposer` controla o campo de mensagem, que cresce até quatro linhas e se reajusta quando a largura muda. A saudação e as sugestões aparecem apenas antes da primeira mensagem. O cabeçalho mantém somente minimizar; o formulário é acessado por “Solicitar demonstração” ou pela ação local das respostas OpenUI, com retorno à conversa. O formulário mostra nome, e-mail e objetivo primeiro; perfil e organização ficam em “Informações opcionais”, preservando os valores ao recolher. `chat-response.css` adapta os componentes oficiais do OpenUI à mesma hierarquia visual, sem mudar o contrato das respostas.

O launcher aparece depois da abertura da landing, sem abrir o painel automaticamente. No primeiro clique, o módulo é carregado sem container intermediário; falhas reais ainda exibem a alternativa de contato. Minimizar preserva conversa e envio. Mudar de rota desmonta o assistente, cancela a geração e ignora respostas obsoletas. Enter envia, Shift+Enter quebra a linha e composição IME não envia acidentalmente. O hover não desloca os controles; as marcas do cabeçalho e do launcher compartilham a mesma proporção interna.

O chat envia texto ao Mistral para responder; não persiste transcrições completas no banco ou no localStorage. Campos do formulário não são enviados automaticamente ao modelo. As condições de retenção/treinamento do provedor dependem da conta e devem ser conferidas antes de publicar; não há promessa de retenção zero.

Contatos são registrados por `POST /api/leads`, independentemente da IA. Nome, e-mail e objetivo são obrigatórios; perfil e organização são opcionais. A confirmação exige recibo após commit SQLite. Timeout de 15 segundos mantém payload/chave imutáveis; tentar novamente recupera o mesmo recibo e não duplica o registro. O mesmo e-mail pode ter solicitações distintas. Registros incluem status, versão, datas e notas com autor.

Limites locais: chat 10 mensagens/minuto/IP, duas gerações/IP e dez globais; leads e login cinco tentativas/15 minutos/IP. Requisições têm body máximo de 64 KiB. A geração encerra após 45 segundos ou 15 segundos sem progresso, propagando cancelamento ao provedor, sem retry automático. Logs não registram texto, contatos, cookies, senhas ou chaves.

## Banco e backup

Banco padrão `data/silent-voice.sqlite`, fora de `public`, ignorado pelo Git. O Vite bloqueia por HTTP os arquivos privados, WAL/SHM, backups e fontes do backend, incluindo caminhos `/@fs/`. O bootstrap recusa um banco configurado sob `public/`, que deve conter apenas assets públicos. `SQLITE_PATH` permite mudar o local. Migrações numeradas são transacionais; foreign keys, WAL e busy timeout estão ativos.

```sh
mkdir -p backups
npm run db:backup -- backups/silent-voice-backup.sqlite
```

O destino deve ser novo. O comando usa a API de backup do driver, incluindo páginas confirmadas no WAL. Para restaurar, pare a API, preserve o banco atual e seus arquivos WAL/SHM e aponte `SQLITE_PATH` para o snapshot restaurado; inicie a API e confira integridade e registros antes de substituir qualquer banco. Não copie somente o `.sqlite` aberto.

## Validação

```sh
npm test
npm run typecheck
npm run build
npm audit
```

A suíte mantém os testes anteriores e acrescenta streaming UTF-8/cancelamento, limites/concorrência, OpenUI seguro, lifecycle do chat, recibo idempotente/retry, banco/backup e autenticação/admin. Fixtures com respostas e contatos fictícios existem somente nos testes. Consulte `docs/reference/chatbot/validation.md` localmente para capturas e limites da conferência manual.

## Publicação futura

Entrega local, sem deploy. Um frontend estático isolado não executa estas APIs. Hospedagem requer processo Node, uma instância inicial, volume SQLite persistente, backup, HTTPS, origem correta e segredo de sessão próprio. O servidor local usa `trustProxy:false` e bind em `127.0.0.1`; atrás de terminação TLS será necessário configurar proxy confiável de forma restrita para cookies Secure e IPs de rate limit, além da escuta adequada. Não habilitar `trustProxy:true` indiscriminadamente. Definir e revisar retenção, aviso de privacidade e operação do contato antes de disponibilizar publicamente.
