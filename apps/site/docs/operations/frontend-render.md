# Frontend estático — Render

Esta etapa publica somente o frontend. Não cria backend, banco, workers ou serviços pagos.

- Repositório: andreiolicar/silent-voice-site
- Branch: deploy/static-frontend
- Serviço: Static Site
- Node: 24.21.0 (.node-version)
- Root directory: vazio (raiz do repositório)
- Build: npm ci --include=dev && npm run build
- Publish directory: dist
- Rewrite: /* → /index.html (Rewrite, não Redirect)
- Nenhuma chave de API, DATABASE_URL ou SESSION_SECRET no frontend.

A configuração está em render.yaml. Criar pelo formulário de Static Site não importa automaticamente o YAML; configurar o rewrite em Settings → Redirects/Rewrites após a criação.

A landing e seus assets funcionam de forma estática. Chat, envio de contatos e login administrativo precisam do backend, que será publicado em outra etapa. O domínio próprio também será conectado separadamente.
