# Hero — hover e ciclo dos personagens

Solicitação: reproduzir o comportamento do carrossel principal da Salte, especialmente hover e barra abaixo da identidade.

Referência inspecionada no navegador: https://web.archive.org/web/20260320135855/https://salte.app/#allan

## Comportamento observado e implementado

- Personagens laterais permanecem em opacidade 0,3 no hover; apenas o cursor indica interação.
- Troca de posição, tamanho e opacidade em 600 ms com `cubic-bezier(0.4, 0, 0.2, 1)`; gradiente e anéis cruzam suas opacidades em 700 ms.
- Na troca, o cartão de identidade desce até bottom -40 px e desaparece em 350 ms. Só então nome, retrato e cor mudam; o cartão retorna à posição aprovada com a mesma duração. O avatar e badge IA têm fade de 500 ms.
- A barra possui trilho de 27 × 3 px e preenche linearmente durante 5 segundos. Seu fim avança o personagem; o intervalo seguinte só começa quando a identidade nova retorna. Mantida Lia como personagem inicial aprovado, seguida por Ravi, Caio e Lia.
- O cartão do nome também é um botão para avançar. Clicar no personagem ativo não reinicia seu ciclo. Cliques nos retratos durante os 650 ms da troca são ignorados, como na referência.
- Seção fora da tela e aba oculta interrompem o ciclo. Ao retornar, começa um novo intervalo completo. Preferência por movimento reduzido mantém controle manual e atualiza a identidade imediatamente.
- No mobile, as margens transparentes das imagens não interceptam mais os cliques nos rostos vizinhos. Uma região de hit-testing no pseudo-elemento limita o alvo, sem recortar os pixels dos retratos.

## Verificação

- Testes primeiro reproduziram a falta de avanço automático, a troca imediata da identidade e a ausência de clique no cartão. Após a implementação, os sete testes focados passaram.
- `npm test`: 301 passaram; 3 integrações PostgreSQL puladas por falta do ambiente dedicado. `npm run typecheck` passou.
- Browser desktop: hover original e local confirmados com opacity 0,3; barra com largura intermediária 8,64 px; avanço automático observado entre agentes; cartão com bottom -30,54 px e opacity 0,135 durante a saída.
- Browser 390 px: sem overflow; hit-testing dos três rostos retorna o respectivo botão, e clique direto no rosto lateral seleciona o agente correto.
- Movimento reduzido: barra sem animação, transição 0 s e nome correspondente ao personagem selecionado.
- Build final e `git diff --check`: passaram. Recarregamento final sem novos erros ou avisos de console.
- Evidência: `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-5-hero.png`.

O carrossel da seção de equipe mantém seu comportamento aprovado. Sem publicação.
