# Revisão 13 — animações dos três cards do Bento

Inspeção do DOM, estilos e ciclos da [referência Salte](https://web.archive.org/web/20260320135855/https://salte.app/#crew-title). Mantidos os textos, o layout dos cards e o verde oficial `#1AA99B`.

## Movimentos aplicados

- **Pequenos sinais. Novas possibilidades.** Pulsos percorrem quatro conexões SVG, chegam ao núcleo, preenchem o anel e saem pelas conexões inferiores. Ciclo de 10 s, com os lados defasados em 5 s e brilho sincronizado.
- **Mais perspectivas. Um mesmo propósito.** As etapas Sinais, Interpretar e Palavras deslizam verticalmente, com pausa, pequeno retorno na chegada e máscara nas extremidades. Ciclo de 10 s. A sequência duplicada torna o reinício contínuo, sem varrer os itens de volta.
- **A sua expressão ganha voz.** Duas órbitas giram em sentidos opostos, em 20 s e 14 s. O ícone central gira em 10 s. Pulsos de luz de 2,4 s se propagam do centro aos anéis.

`ProcessArt.tsx` concentra os diagramas e sua visibilidade; `process-art.css` contém os ciclos. Os elementos permanecem montados quando pausados. Cada diagrama pausa individualmente fora da tela ou quando a página está oculta. Com movimento reduzido, permanece uma composição estática. As ilustrações são decorativas e ficam fora da árvore acessível.

## Verificação

- Conferência no navegador a 1440 px e 390 px; sem overflow horizontal na largura móvel.
- Valores de transformação, rotação e deslocamento SVG mudam durante os ciclos; param fora da tela e retomam ao retornar.
- Emulação de movimento reduzido: todos os elementos decorativos com `animation-name: none` e estado pausado.
- Dois testes novos verificam pausa individual, visibilidade da página, retomada sem remontar, limpeza dos observadores e movimento reduzido.
- Testes do site: 36 de Node e 68 de UI passaram. `npm run typecheck`, `npm run build` e `git diff --check` passaram.
- Capturas: `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-13-bento-motion.png` e `revision-13-bento-motion-mobile.png`.
