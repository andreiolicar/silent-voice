# Revisão 22 — demonstrações dos assistentes

Os três cards da equipe passam a ter composições distintas, seguindo a linguagem de janelas brancas sobrepostas da referência Salte de março de 2026.

- **Caio / azul:** enquadramento da câmera, região dos lábios, ampliação do contorno e uma pista de palavra.
- **Lia / verde da marca:** sensor na neckband, traçado ilustrativo de atividade muscular com repouso/articulação e passagem de sinal a palavra.
- **Ravi / rosa:** uma pergunta na conversa, identificação do assunto e uma resposta articulada; a pergunta, o contexto e a resposta entram em sequência.

`AgentDemo.tsx` contém as três composições; `agent-demo.css` isola os estilos e animações. O retrato existente de Caio é reutilizado. As demonstrações são ilustrativas, sem captura de câmera, microfone ou sensores.

O ciclo de cinco segundos e a navegação por clique/teclado foram preservados. Somente a demonstração selecionada anima; a seção fora da tela e a página oculta pausam a reprodução. Movimento reduzido mostra as cenas completas, sem animações. O slide que sai fica oculto imediatamente para impedir textos sobrepostos durante a entrada do próximo.

Verificação:

- Site: 36 testes Node e 69 testes de UI passaram, incluindo pausa/seleção das demonstrações.
- Typecheck e build do site passaram.
- Inspeção visual em 1440, 768, 390 e 320 pixels; sem overflow horizontal nas duas larguras de celular.
- Conferidas as cenas completas com movimento reduzido e a entrada sequencial da conversa com movimento normal.
- Capturas em `preview-v2/revision-22-agent-{caio,lia,ravi,mobile}.png`, na pasta de trabalho Silent Voice.

Sem mudanças no formulário, header, hero ou Bento de capacidades. Sem publicação.
