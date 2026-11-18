# Revisão 23 — SVGs da landing original

A revisão 22 foi substituída pela linguagem de ilustração já publicada em https://www.silentvoice.com.br/#para-quem, conforme o print e o feedback do usuário. A referência foi inspecionada no navegador e no componente fonte `CardIllustration.tsx`.

## Implementação

- Ravi reutiliza `CommunicationArt` sem redesenhar os balões, telefone ou sua sequência de animação.
- Lia reutiliza `TechnologyArt`, mantendo os painéis e barras originais. A variante EMG troca somente o conteúdo do gráfico e sua legenda por um sinal muscular ilustrativo.
- Caio reutiliza `CareArt`, com uma variante que substitui os dados e a assinatura por contornos de lábios e três momentos da articulação.
- As variantes são opcionais: os três usos da landing antiga mantêm o conteúdo original.
- `AgentDemo` agora compõe o SVG compartilhado. Foram removidos o retrato fotográfico, as janelas HTML, os pequenos textos e as animações CSS específicas da revisão 22.
- As ilustrações usam o verde e os neutros dos tokens originais. Cores externas dos agentes, textos, abas e ciclo de cinco segundos permanecem.

## Auditoria

Características preservadas diretamente do SVG fonte:

- Canvas de 396 × 235, proporções dos painéis e raios próximos de 16,5 unidades.
- Bordas `--color-illustration-panel`, fundos brancos, tonalidade de marca de 12%, ícones de 62% e sombra de 3% de opacidade.
- Gradientes de contorno e preenchimento, fade inferior de 76 unidades e movimento de entrada com as curvas originais.
- Balões de Ravi entram em sequência e permanecem completos. Inspeção aos 3,6 segundos confirmou opacidade 1 em ambos, antes da próxima troca automática.
- Caio e Lia foram conferidos com animação normal após a entrada, além do estado completo com movimento reduzido.
- Conferência em 1440, 768, 390 e 320 pixels. Sem overflow horizontal; em 768 pixels o texto termina em 313px e o canvas começa em 337px.
- Apenas um slide visível por vez; nenhum erro no console durante a auditoria.

Validação: 36 testes Node e 69 testes de UI do site passaram. Typecheck, build e `git diff --check` passaram.

Capturas: `preview-v2/revision-23-original-svg-{caio,lia,ravi,mobile}.png` na pasta de trabalho Silent Voice.

Sem commit, push ou publicação.
