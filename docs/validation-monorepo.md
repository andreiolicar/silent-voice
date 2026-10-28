# Validação da consolidação

Conferência local em 27/10/2026. Referências originais e preservação de histórico estão em [migração](migration.md).

- Testes de resolução comprovam React 19.2.3 único no mobile/RN/renderer; Babel 7.29.7 e módulos nativos resolvem sem duplicação introduzida.
- Admin: 80 testes. Landing: 36 testes Node + 49 UI. API: 61 testes locais; 3 testes PostgreSQL são opt-in. Mobile: 29. Infra: 4. HTTP: 3. UI compartilhada: 2. Total local: 264 aprovados, 3 externos pulados no comando comum.
- Os 3 testes externos passaram separadamente em PostgreSQL isolado: identidade, MFA, sessão durável, CRM concorrente, repetição das migrações e rollback transacional.
- Typechecks e builds dos workspaces web/API aprovados. Build combinado mantém landing, admin e assets independentes.
- Instalações limpas selecionadas de frontend e API passaram sem instalar o runtime mobile. Importação real do módulo de autenticação passou na instalação reduzida da API.
- Mobile: lint, tipos e Prettier aprovados; exportações web, iOS e Android aprovadas. Expo Doctor voltou ao baseline 20/21: seis recomendações de patches já existentes (Expo/constants/font/linking/router/splash). O SDK foi preservado.
- Os três SQL de migração continuam idênticos ao deploy anterior; o contrato OpenUI gerado também.
- Chromium/preview integrado: login, rota de redefinição inválida e landing renderizam seus respectivos apps. Inter e ausência de overflow em 1280 px conferidos. As URLs públicas não mudaram. Pergunta real ao GLM gerou uma resposta OpenUI completa no preview, sem erros de console.

## Limitações e avisos

Exportação não comprova execução em aparelho nem protocolo físico. Android/adb não está disponível neste ambiente; a limitação anterior do simulador iOS não foi declarada resolvida. Não houve nova implementação USB.

`npm audit` encontrou 12 avisos na instalação completa (5 baixos, 3 moderados, 4 altos), concentrados na ferramenta Expo/Vite e suas dependências. A instalação reduzida da API reportou zero. Não foi aplicado `audit fix --force` ou downgrade de Expo. A atualização de ferramentas deve ser tratada em ciclo separado, sem confundir esses avisos com falha dos fluxos testados.

Não foram consumidas tentativas do login do proprietário para validar o corte. O ensaio de autenticação usa banco e identidade sintéticos; a checagem de produção preserva sessões e configuração existentes.

Revisão independente da migração: nenhum achado crítico, importante ou menor. Históricos, 409 hashes dos snapshots, resolução de runtimes e rotas foram reconferidos. Publicação ainda exige o aceite remoto descrito em `deployment.md`.
