# Segurança e dados

- API: credenciais PostgreSQL, Better Auth, Resend e Z.ai somente em `apps/api/.env` local ou no ambiente privado do Render.
- Não publique `.env`, dumps, cookies, sessões, senhas, códigos TOTP/recuperação ou links de redefinição. Prefixos `VITE_` e `EXPO_PUBLIC_` tornam valores públicos.
- Os servidores Vite bloqueiam caminhos privados, fontes da API, documentos, IA e arquivos de banco; isso não substitui manter segredos fora dos bundles e fora do Git.
- CRM exige sessão, e-mail confirmado, papel admin e 2FA no servidor. A landing não cria contas ao captar interesse.
- O chatbot usa um catálogo OpenUI limitado, sem HTML ou ferramentas arbitrárias. Não persiste transcrições completas; campos do formulário não são enviados automaticamente ao modelo.
- Datasets, gravações, dados pessoais, checkpoints e pesos ficam fora do Git comum. Revise licenças, consentimento, retenção e acesso antes de compartilhar dados do reconhecimento.
- Reporte problemas ao mantenedor por canal privado; não publique segredos em issues. Não faça `npm audit fix --force` em produção sem avaliar compatibilidade.

Consulte [autenticação](authentication.md) para a política de sessão/2FA e [deploy](deployment.md) para rollback sem perda de dados.
