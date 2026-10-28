# Validação da consolidação

Conferência local em 27/10/2026. Referências originais e preservação de histórico estão em [migração](migration.md).

- Testes de resolução comprovam React 19.2.3 único no mobile/RN/renderer; Babel 7.29.7 e módulos nativos resolvem sem duplicação introduzida.
- Admin: 80 testes. Landing: 36 testes Node + 49 UI. API: 61 testes locais; 3 testes PostgreSQL são opt-in. Mobile: 29. Infra: 4. HTTP: 3. UI compartilhada: 2. Total local: 264 aprovados, 3 externos pulados no comando comum.
- Os 3 testes externos passaram separadamente em PostgreSQL isolado: identidade, MFA, sessão durável, CRM concorrente, repetição das migrações e rollback transacional.
- Typechecks e builds dos workspaces web/API aprovados. Build combinado mantém landing, admin e assets independentes.
- Instalações limpas selecionadas de frontend e API passaram em diretórios temporários fora de qualquer checkout, sem instalar o runtime mobile. A primeira publicação do frontend detectou um peer React ausente no gerador OpenUI; o teste anterior estava dentro do checkout e enxergava dependências do pai. O erro foi reproduzido fora dele e corrigido incluindo as ferramentas da raiz em `ci:web`. A CI agora inclui jobs separados para os dois builds de produção. Importação real do módulo de autenticação passou na instalação reduzida da API.
- Mobile: lint, tipos e Prettier aprovados; exportações web, iOS e Android aprovadas. Expo Doctor voltou ao baseline 20/21: seis recomendações de patches já existentes (Expo/constants/font/linking/router/splash). O SDK foi preservado.
- Os três SQL de migração continuam idênticos ao deploy anterior; o contrato OpenUI gerado também.
- Chromium/preview integrado: login, rota de redefinição inválida e landing renderizam seus respectivos apps. Inter e ausência de overflow em 1280 px conferidos. As URLs públicas não mudaram. Pergunta real ao GLM gerou uma resposta OpenUI completa no preview, sem erros de console.

## Limitações e avisos

Exportação não comprova execução em aparelho nem protocolo físico. Android/adb não está disponível neste ambiente; a limitação anterior do simulador iOS não foi declarada resolvida. Não houve nova implementação USB.

`npm audit` encontrou 12 avisos na instalação completa (5 baixos, 3 moderados, 4 altos), concentrados na ferramenta Expo/Vite e suas dependências. A instalação reduzida da API reportou zero. Não foi aplicado `audit fix --force` ou downgrade de Expo. A atualização de ferramentas deve ser tratada em ciclo separado, sem confundir esses avisos com falha dos fluxos testados.

Não foram consumidas tentativas do login do proprietário para validar o corte. O ensaio de autenticação usa banco e identidade sintéticos; a checagem de produção preserva sessões e configuração existentes.

Revisão independente da migração: nenhum achado crítico, importante ou menor. Históricos, 409 hashes dos snapshots, resolução de runtimes e rotas foram reconferidos. Publicação ainda exige o aceite remoto descrito em `deployment.md`.

## Aceite em produção

Código publicado: `aba3032db0bb55bcd7ee68d837d2099ac544cf1c`.

- Frontend live: `dep-dbgki867bikc73af4mbg`. API live: `dep-dbgki9om7kps739k2hb0`.
- Os dois serviços apontam para `andreiolicar/silent-voice`, branch `main`, com os planos anteriores preservados.
- As 12 variáveis anteriores da API foram comparadas sem mudanças; apenas `SKIP_INSTALL_DEPS=true` foi acrescentado aos serviços para controlar a instalação.
- Seis rewrites conferidos contra `infra/routes.json`. `/`, `/admin/login`, `/admin/cadastros` e `/conta/redefinir-senha` retornam o HTML correto e JS/CSS válidos, sem fallback HTML nos assets.
- `/api/health`: 200; `/api/auth/get-session` anônimo: 200/null; `/api/admin/leads` anônimo: 401.
- As duas identidades existentes, o administrador verificado com TOTP, o ID da sessão ativa e o cadastro real permaneceram no banco após os rollouts. Nenhuma tentativa de login do proprietário foi consumida.
- Login renderizado no domínio real, sem erros de console. Chatbot respondeu com OpenUI completo em produção. Formulário teve recibo confirmado em banco isolado; nenhum contato sintético foi criado em produção.
- [CI do código publicado](https://github.com/andreiolicar/silent-voice/actions/runs/40612315681): validate, deploy-builds(web) e deploy-builds(api), todos aprovados em Linux.
- Clones originais reconferidos contra os manifestos iniciais: 237 + 172 arquivos, zero diferenças. Os repositórios de origem foram arquivados reversivelmente depois do aceite.

Este registro posterior altera somente documentação; o SHA acima identifica o código em execução.
