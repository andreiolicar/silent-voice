# Polimento visual — header, hero e equipe

Solicitação de 10/11/2026: restaurar o header original do Silent Voice, corrigir o badge IA, eliminar o corte superior do gradiente, colocar a borda dos avatares atrás dos personagens e aproximar o card dos agentes da referência Salte.

## Implementação

- `LandingPage` reutiliza o `Header` original fora do escopo visual V2. O botão Participe aponta para `#lista`; menu móvel, Escape e foco continuam no componente original.
- A fonte efetivamente renderizada foi comparada no navegador: Inter na referência versus SF no primeiro layout local. V2 agora usa a Inter já incluída no projeto.
- Badge IA em SVG, com o mesmo contorno e desenho da referência, incluindo as versões azul, verde e rosa. Os quatro arquivos `ia-badge*.svg` foram obtidos dos recursos carregados pela página de referência fornecida pelo usuário, via pageAssets. O contorno é `/assets/images/shared/ia-badge.svg` na origem. São vetores estáticos sem scripts ou dependências externas. Nenhum retrato da Salte foi incorporado.
- Gradiente separado dos personagens em uma camada própria, com fade branco superior. Altura do carrossel desktop corrigida para 519 px, conforme o layout renderizado a 1440 px, removendo 61 px extras. Fade inferior termina suavemente no branco.
- Nos avatares, a borda decorativa ocupa z-index 1 e o retrato z-index 2 dentro de um contexto isolado, eliminando a faixa sobre a cabeça.
- Card desktop: largura 860 px, interior 370 px, raios 24/20 px, faixa inferior 68 px. Distância do início da seção ao card: 297 px. Editor flutuante 550 × 92 px sobre painel de captura 512 × 205 px; alinhamento dos status corrigido para não cortar o texto.
- A demonstração de visão usa uma sequência de pontos de articulação labial, dentro da composição visual da referência. Os três agentes compartilham o mesmo editor e estrutura; áudio usa ondas e EMG usa o sinal muscular.
- Em telas pequenas, o painel de captura começa abaixo do editor e a barra de ferramentas cabe na largura disponível. O áudio mantém as partes ativa e inativa da onda visíveis.

## Verificação

- Comparação visual iterativa no navegador a 1440 × 1000, com hero e equipe capturados na mesma escala da referência. A composição e as medidas comuns foram conferidas; retratos, neckband, textos e diagrama de visão permanecem próprios do Silent Voice.
- Inspeção em 390 px e 320 px sem overflow horizontal; seleção dos três agentes; menu original abre, fecha com Escape e devolve o foco ao botão.
- Recarregamento final sem novos erros ou avisos de console.
- `npm test`: 296 testes passaram; 3 integrações PostgreSQL permaneceram puladas por falta do ambiente dedicado.
- `npm run typecheck`, `npm run build` e `git diff --check`: passaram.
- Evidências locais em `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-3-hero.png` e `revision-3-team.png`.

Sem publicação ou alteração da API e banco de produção nesta revisão.
