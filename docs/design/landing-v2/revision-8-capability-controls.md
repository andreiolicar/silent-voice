# Revisão 8 — progresso circular e ícones das capacidades

## Referência inspecionada

[Salte — captura de 20/03/2026](https://web.archive.org/web/20260320135855/https://salte.app/#crew-title), script do seletor `.cap-item`: ciclo de 5000 ms, circunferência 163.36, SVG 58 × 58 com raio 26 e traço 2.5 de pontas arredondadas. Início no topo, preenchimento no sentido horário. Seleção por clique; selecionar o item ativo não reinicia o ciclo. A entrada da seção na viewport inicia um intervalo completo. O hover não seleciona.

## Correção

O controle anterior era uma borda CSS fixa com um segmento transparente, sem progresso ou avanço automático, e selecionava opções no hover/foco. Agora usa SVG com `stroke-dashoffset` de 163.36 a 0 durante os mesmos 5000 ms do temporizador compartilhado. O avanço automático percorre Visão → Sinais musculares → Áudio → Visão. Selecionar outra opção inicia um ciclo completo; clicar na opção atual mantém o intervalo. Animações param fora da viewport ou com a página oculta; ao voltar, o ciclo recomeça. Movimento reduzido mantém seleção manual e um anel completo estático.

Ícones SVG próprios em `apps/site/src/v2/CapabilityIcon.tsx`: silhueta de percepção, núcleo de sinais e fones de áudio, com preenchimentos sólidos e `currentColor`. Disco interno 40 × 40, desenho 24 × 24, aro externo 58 × 58. Azul ativo `#0E7AFF` sobre `#031833`; cinza inativo sobre `#1C1C1C`. Identificação textual e navegação por setas/Home/End preservadas. O carrossel de retratos continua com sua regra anterior de reiniciar ao clicar no item ativo.

## Verificação

- Navegador: duração calculada de 5 s. O dashoffset de Visão caiu de 150.304 para 84.3976 em aproximadamente 2.018 s; 3.212 s depois o estado já era Sinais musculares e seu novo arco estava em 143.21. Hover sobre Áudio não mudou a seleção.
- Desktop 1440 × 1000 e celular 390 × 844 conferidos; sem rolagem horizontal. Movimento reduzido: `animation-name: none` e offset 0 no item ativo.
- Quatro testes novos cobrem ciclo, hover, clique no item ativo, reinício ao selecionar outro, teclado, página oculta e movimento reduzido. Suíte completa passou, incluindo 66 testes da área site; integrações PostgreSQL continuam ignoradas por configuração.
- `npm run typecheck`, `npm run build` e `git diff --check` passaram.
- Capturas em `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-8-bento-controls.png` e `revision-8-bento-controls-mobile.png`.
