# Revisão 11 — formulário final

Referência inspecionada no navegador: [Salte, captura de 20/03/2026](https://web.archive.org/web/20260320135855/https://salte.app/#crew-title), formulário final e capturas enviadas pelo usuário.

## Ajustes

- Botão com texto branco, fundo no verde oficial `#1AA99B`, peso 600, altura 50 px e fonte 14/20 px no desktop. Abaixo de 768 px, altura 42 px e fonte 12/20 px, conforme a referência.
- Corrigida a herança de `font: inherit`, que fazia o botão aparecer em 16 px e peso 400. A correção fica restrita ao formulário.
- Campo com largura máxima 466 px, espaçamento 10 px, borda de 1 px, raio 16 px, padding 8/8/8/16 px e ícone de envelope arredondado 18 × 18 com traço 1.2 px. Input em 14/20 px também no celular.
- Estados de hover, foco e clique seguem o comportamento visual do botão de referência, com a cor da marca.
- Removidos “Um convite para acompanhar. Sem compromisso de compra.” e o bloco “Sobre o uso do seu e-mail”, incluindo CSS sem uso e associação ARIA ao texto removido. A associação ARIA às mensagens de erro continua ativa quando necessário.
- Mensagens funcionais de envio, erro e sucesso permanecem. Nenhuma mudança na integração de cadastro.

## Verificação

- Viewport 687 px: referência e Silent Voice com campo de 466 × 60 px e botão de 105.49 × 42 px; fonte 12/20 px, peso 600. Texto do botão local RGB 255, 255, 255.
- Desktop 1440 px: formulário com 68 px de altura, botão com 50 px e fonte 14/20 px, igual à referência nessa largura.
- Celular 390 px: campo de 326 × 60 px. Largura 320 px também sem rolagem horizontal ou quebra de linha do botão.
- `npm test`: 305 testes passaram; 3 integrações PostgreSQL ignoradas por configuração. `npm run typecheck`, `npm run build` e `git diff --check` passaram.
- Capturas em `/Users/andrei/Documents/ChatGPT/Silent Voice/preview-v2/revision-11-footer-form.png` e `revision-11-footer-form-mobile.png`.
