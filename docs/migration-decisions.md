# Decisões da migração

Registro completo das decisões de execução e seus limites. A tentativa nested foi substituída pela resolução final hoisted; as entradas anteriores permanecem para explicar a decisão. Nenhuma sugestão menor foi adiada pela revisão.

- Ruling: user approved executing the complete consolidation, so preserve mobile working changes in a monorepo snapshot commit; do not commit/push the original mobile repo — otherwise auth/design work could be lost or mixed with unrelated source publication.

- Ruling: fresh clone at /Users/andrei/silent-voice-monorepo provides isolation without touching original clones/servers — using the old source cwd would mutate the wrong GitHub repo.

- Ruling: approved architecture in chat is the design approval; write spec/plan and execute without another approval round per user instruction — cost if wrong is a migration structure they may want adjusted, reversible on feature branch before cutover.

- Task 2 Ruling: npm nested install strategy preserves web19.3/mobile19.2 and prevents hoisted RN/renderer resolving web React — hoisted run reproduced invalid dispatcher; cost is larger/slower dependency installation. No source dependency upgrades. Extra shared http-client package contains the existing readiness function used by site and admin, avoiding UI/network duplication.

- Task 2 Ruling: remove hardcoded node_modules font preload from HTML, keeping same Inter font through the existing font CSS — dependency paths vary by monorepo layout — cost: small resource-hint performance change, no visual font change.

- Task 3 Ruling: supersede nested strategy with hoisted dependencies anchored to mobile React19.2.3 at root; web keeps local19.3 and Vite dedupe — actual Expo export failed Babel peer resolution and duplicate native modules under nested; preserve original expo-asset57.0.15 and add explicit Babel7.29.7 — cost is root mobile React dev anchors, covered by resolution and filtered-install tests.

- Task 3 Ruling: root TypeScript6.0.3 anchor keeps eslint/expo on its supported compiler; web/API retain local7.0.2. Vitest inlines dependencies so hoisted React consumers use each web app dispatcher — observed lint/compiler failure and invalid hooks in existing tests — cost: explicit test bundling and three small root dev anchors, no app version upgrades.

- Final: Ruling: existing auth/product design remains as approved — migration preserves it rather than reopening UI/features — cost: preexisting product limitations stay.

- Final: Ruling: native/hardware claims remain limited to exports and tests — no available physical validation or new transport — cost: device/deep-link validation remains separate.

- Final: Ruling: existing Expo patch/audit warnings are reported, no forced upgrades — source versions and SDK preservation are binding — cost: maintenance warnings remain for a follow-up.

- Final: Ruling: production acceptance requires post-cutover checks, not the review verdict — validate live assets/API/session metadata and chat before archive — cost: rollback if remote behavior differs.

- Final: Ruling: source clones untouched by our commands; review verifies imported manifests rather than monitoring concurrent external edits — no writes performed to original repos — cost: another process could independently change them.

- Final: Ruling: approved monorepo execution includes canonical GitHub integration and controlled Render cutover; skip finishing-skill option menu because user already selected this outcome — cost if misunderstood is reversible integration/publication, preserving origins for rollback.

As conferências posteriores de produção e dos clones de origem estão em [validação](validation-monorepo.md). A falha do primeiro build reduzido e a correção são registradas ali; os jobs independentes de CI evitam repetir a falsa validação por dependências do diretório pai.
