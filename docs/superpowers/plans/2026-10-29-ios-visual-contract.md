# iOS Visual Contract Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for this single-task continuation.

**Goal:** Incorporar o contrato preliminar e as fixtures de João à regressão mobile.

**Architecture:** Módulo TypeScript puro no caminho do handoff, sem consumidor de UI ou adaptador nativo. Fixtures ficam em testes e não entram no bundle do aplicativo.

**Tech Stack:** Expo 57 existente, TypeScript, Node 24 e node:test.

**Spec:** `docs/superpowers/specs/2026-10-29-ios-visual-contract-design.md`; contrato e testes do IOS-HANDOFF-02.4.

## Global Constraints

- Preservar as mudanças da build iOS e as dependências existentes.
- Não alterar parâmetros do gate temporal ou inventar reconhecimento.
- Não adicionar captura, modelos, dados pessoais ou efeitos remotos.
- Sem commit, push ou publicação.

## Review Focus

- Flag de runtime disponível sem implementação: resultado continua indisponível.
- Entrada vazia ou com apenas um frame: bloquear sem exceção.
- Espelhamento: aceitar somente `false` explícito.
- Timestamps absolutos grandes: subtrair antes de converter para number.
- Fixture temporal: comparar com a referência recebida, sem gerar expectativa pelo código testado.

### Task 1: Adotar o módulo e seus testes

**Files:**
- Create: `apps/mobile/src/features/visual-recognition/contract.ts`.
- Create: `apps/mobile/tests/visual-recognition.test.mjs`.
- Create: `apps/mobile/tests/visual-recognition-fixture.test.mjs`.
- Create: `apps/mobile/tests/fixtures/visual-recognition.json`.
- Create: `apps/mobile/docs/visual-recognition-handoff.md`.

**Interfaces:** Preservar as exportações e assinaturas do pacote, incluindo `analyzeCapture(frames, options?)` e `startGlobalRecognition({ available })`.

- [x] Incorporar os testes recebidos, adaptando somente caminhos da fixture; observar a ausência do módulo no projeto.
- [x] Incorporar o contrato recebido e formatar segundo o projeto; rodar os 11 casos originais.
- [x] Cobrir captura vazia/incompleta e indisponibilidade mesmo com `available: true`.
- [x] Documentar hashes de origem, alterações de integração e limitações.
- [x] Executar os checks exigidos do monorepo e revisão independente; registrar resultados.

## Execution record

Continuação solicitada pelo operador após a validação da build física. Este incremento adota o material já recebido; não inaugura o caminho de câmera/R4.

Os dois arquivos de teste primeiro falharam por ausência do módulo no workspace (`ERR_MODULE_NOT_FOUND`). Após incorporar o contrato recebido, os 13 casos passaram. O contrato foi confirmado byte a byte igual à origem, e a fixture reformatada foi confirmada profundamente igual ao JSON original.

Checks executados após a integração: `npm test` (42 testes mobile aprovados, zero falhas no monorepo; três testes PostgreSQL ignorados pela configuração existente), `npm run typecheck`, `npm run build` e `npm run check:mobile` passaram. Não houve mudança de dependência, nova build nativa ou operação de assinatura. Os seis desalinhamentos de patch Expo já registrados no ciclo anterior não foram alterados.

Decisões de execução: reutilizar checkout/branch existentes conforme a continuidade da sessão; preservar integralmente o contrato recebido; manter a fixture completa como referência, deixando explícito que somente sua seção temporal é comparada. Sem commit ou push.

Revisão independente concluída sem problemas acionáveis. O revisor conferiu a preservação dos dez testes originais, a adaptação do caso temporal, os hashes/valores de origem e a ausência de consumidores de UI/runtime, e executou novamente os 13 testes focados com sucesso.
