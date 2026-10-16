# Interface administrativa — CRM

Referência: quarta tela, **CRM Dashboard**, no [arquivo editável do Figma](https://www.figma.com/design/XayIQpxA63MQGsqhhBfoBd/dashboards--c%C3%B3pia-?node-id=1-7539). Frame `1:7539`; contexto de sidebar `1:7540`, barras `1:7634`/`1:7662`, células `1:7745`/`1:7750` e inspector `1:8215`/`1:8227`.

## Composição

- Sidebar de 260 px, recolhível para 64 px; itens com altura mínima de 32 px e quebra de linha; topbar e toolbar de 54 px.
- Tabela com linhas de no mínimo 48 px, divisórias finas e cabeçalho claro. Ações compartilham `AdminButton`: pílula de 28 px, texto de 12 px, ícones de 14 px, padding lateral de 12 px e intervalo de 6 px. Dados longos quebram linha e expandem a altura sem reticências.
- Detalhes em coluna lateral de 395 px, com cabeçalho de no mínimo 46 px e nome completo com quebra de linha. A tabela tem rolagem horizontal própria quando o painel estiver aberto em larguras menores.
- Inter, verde `#1AA99B` e azul-marinho `#051B34`. Tokens do CRM centralizados no escopo `.crm-layout` são aliases dos tokens da landing: superfícies, bordas, texto, marca e estados. Nenhuma cor literal permanece nos arquivos CSS administrativos; as sombras também derivam desses tokens.
- Ícones [Lucide React](https://lucide.dev/guide/react), importados individualmente em um componente tipado: 16 px, traço 1,65 e cor herdada. Hover e estado ativo da sidebar usam a mesma faixa de largura total; o ativo mantém o marcador verde. A marca no CRM tem aproximadamente 152 px de largura. Nenhuma captura da referência é usada como interface.

## Navegação e dados

`/admin` apresenta os totais globais por status e os cinco cadastros mais recentes. `/admin/cadastros` oferece busca, filtros de status e data, paginação de 25 registros, exportação CSV da página e detalhes com status e anotações.

`/admin/acompanhamento` centraliza Novo, Em contato, Demonstração combinada e Encerrado numa única entrada da sidebar. Os quatro filtros internos mostram contadores globais e usam o parâmetro `status`; voltar e avançar no navegador atualiza a seleção, mantendo busca e datas aplicadas. Sem status válido, a seleção inicial é Novo. Limpar os filtros conserva o status de acompanhamento. A Visão geral aponta seus totais para essa rota; Cadastros continua mostrando a lista completa.

Exportação escapa o CSV e mantém fórmulas de planilha como texto. Nenhum cadastro ilustrativo foi inserido na base real.

Autenticação, CSRF, expiração de sessão, controle de versão e rascunhos em memória foram preservados. O painel lateral não prende o Tab nem bloqueia a rolagem da página; Escape fecha os detalhes e restaura o foco. Aplicar filtros de data retorna o foco ao controle persistente; Enter na busca conserva o foco na busca.

O login continua sem logo, com card de raio 12 px e campos/botão em pílula de altura 44 px. O grid permite reduzir o card até 358 px em uma viewport de 390 px, sem rolagem horizontal. Labels e valores dos campos continuam à esquerda; título e feedback ficam centralizados. Landing page e chatbot não foram redesenhados nesta alteração.

## Foco e estados dos controles

- O escopo administrativo define seu foco a partir de verde da marca e azul-marinho, sem alterar o token de foco global da landing.
- Botões, links e sidebar usam contorno de 1 px, afastado 2 px; na sidebar ele fica para dentro da faixa para não ser cortado.
- Campos usam borda de 1 px e halo turquesa de 2 px a 12% de opacidade. Busca e seletor de status aplicam o indicador somente ao contêiner, evitando bordas de foco duplicadas.
- Hover de campos altera suavemente a borda; os estados desabilitados e as dimensões aprovadas são preservados.
- Alto contraste usa `Highlight` do sistema e contorno de 2 px. Movimento reduzido desativa as transições.

## Verificação

- Suíte completa: `npm test` (69 testes Node + 77 testes UI). Inclui os quatro status, histórico do navegador, preservação de busca/datas, limpeza na segunda página, contadores e integração da sidebar.
- Tipagem: `npm run typecheck`; compilação: `npm run build`.
- Chromium: conferência visual em 1920, 1440 e 1280 px; sidebar, tabela, inspector, navegação por status, histórico do navegador e foco dos filtros. Botões medidos em 28 px, fonte 12 px e ícones 14 px; sem rolagem horizontal global. O filtro de datas também foi conferido em 390 px e ficou contido na área disponível. Dados de conferência foram respondidos apenas na aba de teste, sem alterar o banco.
- Safari: nesta revisão a sessão existente estava expirada e levou ao login. A tela protegida com os novos filtros foi validada no Chromium e nos testes de componentes; nenhuma credencial ou conta foi alterada.
- Capturas locais em `docs/reference/admin-v2/` (ignoradas no Git). Capturas povoadas são identificadas como dados ilustrativos de QA.
- Revisão de foco: login, busca, seletor, datas, botões, anotações e sidebar conferidos com mouse e teclado no Chromium. Alto contraste e movimento reduzido foram emulados e restaurados ao terminar. Capturas `login-rounded-final.png` e `dashboard-soft-focus.png` registram o ajuste.

Entrega local na branch `chatbot-backoffice`, sem publicação ou alteração de senha. Lucide React é a dependência adicionada para os ícones solicitados. Servidores frontend e API mantidos em execução.
