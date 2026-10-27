# Integração GLM-4.5-Flash — 20/10/2026

O chatbot usa a API comum da Z.ai, com o modelo `glm-4.5-flash`,
`ZAI_API_KEY` somente no servidor e thinking desativado. Não há fallback
automático para modelos pagos. O `.env` local não foi alterado.

## Validação automatizada

- `npm test`: 166 testes aprovados (78 Node e 88 de interface).
- `npm run build`: aprovado, incluindo typecheck de frontend e servidor.
- `git diff --check`: aprovado.
- A chave configurada não aparece nos arquivos do build público.
- Adapter: UTF-8 fragmentado, SSE/CRLF, raciocínio excluído, término explícito,
  truncamento, erros HTTP, frames inválidos/grandes e cancelamento.

## Validação real

Na landing local, em Chromium pelo navegador integrado:

- A sugestão “Como o dispositivo funciona?” recebeu e renderizou uma resposta real.
- Uma pergunta sobre o aplicativo, enviada com Enter na mesma conversa,
  recebeu e renderizou a lista de recursos.
- A solicitação de demonstração, enviada pelo botão, recebeu uma resposta
  com `ContactAction`; clicar abriu o formulário local.
- Não foi enviado nenhum cadastro nem criado contato de teste no banco real.
- Vite permaneceu ligado; somente a API foi reiniciada para carregar o provider.
- Captura local: `docs/reference/chatbot/v2/glm45-live.png`.

## Limites

A validação confirma o fluxo local e respostas reais, sem garantir precisão de
todas as respostas ou disponibilidade do serviço gratuito. Não foi realizado
teste de carga, nem conferência desta integração no Safari. As cotas são as da
conta Z.ai. A implantação pública e uma revisão mais ampla da copy da landing
não fazem parte desta alteração.
