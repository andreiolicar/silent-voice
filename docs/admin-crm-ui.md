# Interface administrativa — CRM

Referência: quarta tela, **CRM Dashboard**, no [arquivo editável do Figma](https://www.figma.com/design/XayIQpxA63MQGsqhhBfoBd/dashboards--c%C3%B3pia-?node-id=1-7539). Frame `1:7539`; contexto de sidebar `1:7540`, barras `1:7634`/`1:7662`, células `1:7745`/`1:7750` e inspector `1:8215`/`1:8227`.

## Composição

- Sidebar de 260 px, recolhível para 64 px; topbar e toolbar de 54 px.
- Tabela com linhas de 48 px, divisórias finas, cabeçalho cinza claro e ações compactas de 30 px.
- Detalhes em coluna lateral de 395 px, com cabeçalho de 46 px. A tabela tem rolagem horizontal própria quando o painel estiver aberto em larguras menores.
- Inter, verde `#1AA99B` e azul-marinho `#051B34`. Tokens do CRM centralizados no escopo `.crm-layout`, consumidos pela tabela, visão geral e inspector.
- Ícones SVG locais em `public/assets/admin/`, exportados do Figma e preservados em suas dimensões intrínsecas. Nenhuma captura da referência é usada como interface.

## Navegação e dados

`/admin` apresenta os totais globais por status e os cinco cadastros mais recentes. `/admin/cadastros` oferece busca, filtros de status e data, paginação de 25 registros, exportação CSV da página e detalhes com status e anotações.

Os links de acompanhamento usam o parâmetro `status`; voltar e avançar no navegador atualiza o filtro e a seleção da sidebar. Exportação escapa o CSV e mantém fórmulas de planilha como texto. Nenhum cadastro ilustrativo foi inserido na base real.

Autenticação, CSRF, expiração de sessão, controle de versão e rascunhos em memória foram preservados. O painel lateral não prende o Tab nem bloqueia a rolagem da página; Escape fecha os detalhes e restaura o foco. Aplicar filtros de data retorna o foco ao controle persistente; Enter na busca conserva o foco na busca.

O login aprovado continua sem logo, com card/campos/botão de raio 12 px e campos/botão de altura 44 px. Landing page e chatbot não foram redesenhados nesta alteração.

## Verificação

- Suíte completa: `npm test` (69 testes Node + 72 testes UI).
- Tipagem: `npm run typecheck`; compilação: `npm run build`.
- Chromium: conferência visual em 1920, 1440 e 1280 px; sidebar, tabela, inspector, navegação por status, histórico do navegador e foco dos filtros. Dados de conferência foram respondidos apenas na aba de teste, sem alterar o banco.
- Safari: sessão real existente, visão geral, navegação para cadastros e estado vazio. A base estava vazia; o inspector com dados foi conferido no Chromium e nos testes de componentes.
- Capturas locais em `docs/reference/admin-v2/` (ignoradas no Git). Capturas povoadas são identificadas como dados ilustrativos de QA.

Entrega local na branch `chatbot-backoffice`, sem publicação, alteração de senha ou dependências novas. Servidores frontend e API mantidos em execução.
