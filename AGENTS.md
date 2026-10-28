# Silent Voice — instruções do monorepo

- Leia o README e as instruções da área antes de editar. Instale dependências apenas na raiz com `npm ci`; mantenha um lockfile.
- Não altere versões/SDK como parte de refatorações. Web usa React 19.3; mobile usa React 19.2.3/Expo 57/RN 0.86.3. A raiz ancora o React nativo; web mantém sua versão local e dedupe no Vite. Preserve os testes de resolução de runtimes.
- `apps/site` e `apps/admin` podem importar `packages/web-ui`; mobile não importa DOM/CSS. API não importa fontes de frontend.
- `packages/contracts` contém contratos neutros. Mudanças precisam considerar os consumidores e revisão dos responsáveis.
- IA de reconhecimento fica em `ai`; o chatbot comercial fica na API. Não invente protocolo ou runtime para o núcleo sem decisão da equipe.
- Preserve componentes e comportamentos aprovados, acessibilidade, foco e movimento reduzido.
- Segredos só no ambiente privado do serviço. Nunca em `VITE_*`, `EXPO_PUBLIC_*`, fixtures, logs ou commits. Não inicie API contra produção para testar: o startup aplica migrações.
- Não apague dados, altere infraestrutura, publique, faça commit/push ou mude permissões sem autorização na sessão. A consolidação inicial foi autorizada; isso não autoriza publicações futuras.
- Valide a área alterada e execute `npm test`, `npm run typecheck`, `npm run build` antes de integrar. Mudanças mobile também exigem `npm run check:mobile` e documentação Expo 57.
- Relate limitações reais. Exportar o app não comprova execução nativa/hardware.
