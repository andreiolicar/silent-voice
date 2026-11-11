# Carrossel — comportamento da referência

Solicitação: reproduzir a interação dos três avatares da Salte, com hover discreto e animações no clique e na troca de card.

Referência inspecionada no navegador: https://web.archive.org/web/20260320135855/https://salte.app/#assistentes

## Medidas observadas e implementadas

- Hover altera apenas o cursor; não seleciona nem realça o avatar inativo.
- Pressão: escala 0,95, transição de 200 ms com `cubic-bezier(0.34, 1.56, 0.64, 1)`. A barra permanece fixa enquanto o retrato se comprime.
- Opacidade dos avatares: 0,2 → 1 em 300 ms; trilho de progresso com transição de opacidade de 300 ms.
- Cards simultaneamente montados, com fade cruzado de 500 ms e `cubic-bezier(0.4, 0, 0.2, 1)`. Fundo e borda mudam em 500 ms.
- Ciclo de 5 segundos com preenchimento linear da barra de 27 × 3 px. Clicar reinicia o ciclo e a demonstração, inclusive no agente já selecionado.
- Observação da seção com margem vertical de 50 px: sair de tela interrompe o ciclo; retornar começa um novo intervalo. Aba oculta também suspende o timer.
- Movimento reduzido mantém seleção manual, desliga o ciclo e remove as transições. Cards inativos são `aria-hidden` e `inert`; teclado continua funcional.
- As três camadas usam a mesma célula do grid, preservando a altura durante a troca, inclusive no mobile.

## Verificação

- Testes de comportamento reproduziram primeiro as falhas de seleção no hover e ausência do ciclo; passaram após a implementação.
- Navegador: hover sem seleção; pressão sem antecipar a seleção; frames intermediários com opacidades 0,761352 e 0,238648 durante o fade; reinício da barra em 0 px; mesmas curvas e durações da referência.
- Desktop 1440 px: card permanece 860 × 442 px. Mobile 390 px: altura estável de 510 px para os três agentes, sem overflow horizontal.
- Preferência de movimento reduzido verificada no navegador: transição 0 s e barra sem animação. Recarregamento final sem novos erros ou avisos de console.
- `npm test`: 299 passaram e 3 integrações PostgreSQL puladas por falta do ambiente dedicado. Os cinco testes focados foram repetidos após completar a tipagem do mock de MediaQueryList.
- `npm run typecheck`, `npm run build` e `git diff --check`: passaram.
- Evidência: `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-4-carousel.png`.

Mudanças limitadas ao carrossel de equipe; o seletor de capacidades mantém seu comportamento anterior. Sem publicação.
