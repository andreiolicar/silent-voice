# Revisão 12 — composição do fundo final

Inspeção direta do DOM e dos estilos computados da [referência Salte](https://web.archive.org/web/20260320135855/https://salte.app/#crew-title).

## Causa da diferença

O fundo local encerrava a faixa branca em 15% da altura; a referência mantém branco até 45%. Os três círculos anteriores tinham bordas de verde direto, sem sombra ou máscara superior, e apareciam marcados já atrás do título. A referência usa quatro círculos sobrepostos em uma tinta clara, com opacidade, sombras e uma camada branca sobre a parte superior.

## Composição aplicada

- Gradiente vertical branco em 0–45%, tinta 10% da marca em 70% e tinta 30% em 100%, equivalentes à proporção azul/branco da referência, usando `#1AA99B`.
- Quatro halos: 980, 750, 536 e 333 px; centro em `calc(50% + 39px)`. Escala 0.5 abaixo de 768 px.
- Cor dos halos: 40% da marca com branco. Preenchimento de transparente a 35% de alpha, borda de 2 px/15% de alpha, opacidade global 0.45, sombra 0 4px 12px/6% preto.
- Máscara branca sobre os primeiros 45% da seção, sólida até a metade dessa camada e transparente na base. Conteúdo sobre as camadas decorativas e sem interceptação de cliques.
- Altura mínima desktop 466 px, como a referência. Em telas menores a altura acompanha o conteúdo, com 64 px abaixo do formulário.

## Verificação

- Comparação visual lado a lado a 1440 px: referência e Silent Voice com fundo de 1400 × 466 px. Mantidas as medidas aprovadas do campo e do botão.
- Conferidos 687 e 390 px, quatro círculos presentes, escala mobile 0.5 e sem rolagem horizontal.
- Testes do site: 36 de Node e 66 de UI passaram. `npm run typecheck`, `npm run build` e `git diff --check` passaram.
- Capturas em `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-12-footer-background.png`, `revision-12-footer-background-desktop.png` e `revision-12-footer-background-mobile.png`.
