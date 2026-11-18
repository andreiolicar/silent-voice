# iOS Front Capture Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans in this session; one independent final review. Do not commit or push.

**Goal:** Executar um ensaio sintético nativo/Hermes e uma aquisição frontal de quatro segundos no iPhone.

**Architecture:** Módulo local Expo/AVFoundation, adaptador TypeScript e rota de laboratório condicionada à flag pública de build. Adquirir somente metadados reais; manter buffers efêmeros e reconhecimento indisponível.

**Tech Stack:** Expo 57, Swift 5.9, AVFoundation, XCTest e node:test; sem novas dependências npm.

**Spec:** `docs/superpowers/specs/2026-10-29-ios-front-capture-design.md`, aprovado na sessão.

## Global Constraints

- Preservar versões, sessão autenticada, fluxo USB e alterações anteriores.
- Câmera somente após ação explícita; sem microfone, arquivos de imagem, inferência ou dados pessoais em logs.
- Reportar BGRA32/retrato como origem real, sem fingir normalização BGR8.
- Finalizar câmera ao cancelar, perder foco, sair da tela ou entrar em background.
- Reutilizar a branch local existente. Sem commit, push ou publicação.

## Review Focus

- Cancelamento durante início/configuração: resultado único e câmera encerrada.
- Frame inexistente, repetido, regressivo ou coleção excessiva: erro limitado e controlado.
- Entrada em background ou interrupção AVFoundation: descarte e encerramento.
- Módulo ausente/flag desligada: ensaio indisponível, sem fallback fictício.
- Relatório de origem BGRA/portrait: bloqueio do contrato congelado, sem reconhecimento.

### Task 1: Acumulador temporal e módulo de captura

**Files:** `apps/mobile/modules/silent-voice-capture/{expo-module.config.json,Package.swift,ios/*.swift,ios/SilentVoiceCapture.podspec,Tests/CaptureTimelineTests.swift}`.

**Interfaces:** Módulo `SilentVoiceCapture` com `getPermission`, `requestPermission`, `syntheticFrames`; view com `capture(): Promise<NativeCaptureReport>` e `cancel(): Promise<void>`. `NativeCaptureReport` definido na spec.

- [x] Escrever testes Swift de precisão, monotonicidade, término, limite e reset; observar falha antes do acumulador.
- [x] Implementar acumulador limitado e confirmar testes verdes.
- [x] Implementar AVFoundation frontal, permissão e preview. Resolver resultados na fila serial e interromper em todos os caminhos; liberar frames nos callbacks.

### Task 2: Adaptador, diagnóstico e área de ensaio

**Files:** `apps/mobile/src/features/visual-recognition/{capture-diagnostics.ts,native-capture.tsx,IosCaptureLabScreen.tsx}`, `apps/mobile/tests/visual-capture.test.mjs`, `apps/mobile/app/ios-lab.tsx`, `apps/mobile/app/_layout.tsx`, `apps/mobile/src/features/initial-flow/screens/SplashScreen.tsx`, `apps/mobile/app.json`.

**Interfaces:** Consumir as funções/view da Task 1. `verifySyntheticCapture(frames)` deve verificar timestamps literais e mapeamento usando o contrato congelado. `summarizeCapture(report)` deve preservar status/erros reais e reportar métricas sem fabricar frames normalizados.

- [x] Escrever testes de diagnóstico: origem real incompatível, timestamps adulterados, flag/ausência de módulo e captura cancelada; observar falha antes das funções.
- [x] Implementar funções puras e adaptador; confirmar testes verdes.
- [x] Adicionar rota condicionada a iOS + `EXPO_PUBLIC_ENABLE_IOS_LAB=1`, controles explícitos, preview, estados e cancelamento por perda de foco/background. Adicionar somente `NSCameraUsageDescription`.

### Task 3: Verificar e testar no aparelho

**Files:** `apps/mobile/docs/ios-front-capture.md`, este registro e eventuais correções de regressão.

- [x] Rodar suíte Swift, testes raiz, typecheck, build e check:mobile; registrar Expo install check/Doctor sem upgrades.
- [x] Revisão independente da implementação, corrigindo problemas relevantes.
- [x] Prebuild sem instalar npm/sem clean, restaurar scripts se o gerador os alterar e instalar pods locais.
- [x] Build Release local com flag de ensaio e `COCOAPODS_PARALLEL_CODE_SIGN=false`; validar assinatura e instalar.
- [x] Abrir laboratório, executar teste sintético e captura/cancelamento no iPhone com operador; registrar evidência e limites, sem imagem persistida.

## Execution record

Andrei aprovou o design e a execução física. O módulo Expo local foi identificado pelo autolinking, incluído nos pods e compilado para iOS. O build Release com flag de ensaio e assinatura serial terminou em `BUILD SUCCEEDED`; a assinatura passou em `codesign --verify --deep --strict`. A instalação e a abertura de `br.com.silentvoice.mobile.dev` no iPhone 13 (iOS 26.6.2) foram confirmadas por devicectl.

Verificação de código: quatro testes Swift e 47 testes mobile aprovados; `npm run typecheck`, `npm run build` e `npm run check:mobile` passaram. A execução final de `npm test` passou, com três testes PostgreSQL ignorados conforme configuração existente. Uma repetição concorrente à compilação nativa falhou em `apps/admin/src/App.test.tsx`, no teste de entrada direta do admin, por não encontrar o campo E-mail dentro do prazo; uma nova execução completa sem a compilação concorrente passou sem alterações no admin. Não atribuir causa definitiva somente por essa correlação.

Expo install check e Doctor continuam reprovando apenas os seis desalinhamentos de patch já existentes, sem upgrades. O gerador prebuild recriou a pasta iOS e alterou automaticamente os scripts npm; os scripts foram restaurados e não há diff em package.json/lockfile.

A revisão independente encontrou um defeito P2: o retorno do laboratório sempre direcionava ao login. A política foi isolada em `lab-navigation.ts`; o teste reproduziu a falha com sessão existente, depois passou com os destinos Home/login/onboarding corretos. Não houve outros achados acionáveis. Não houve segunda revisão; a correção foi coberta pelo teste e suíte completa.

O Device Hub informou que o espelhamento requer iOS 27; não foi feita atualização do iPhone. Na primeira tentativa de abertura o operador viu o laboratório brevemente e depois uma tela preta. O processo deixou de estar em execução e a consulta de crash logs filtrada por SilentVoice não encontrou arquivo. A reabertura pelo devicectl foi estável e o operador confirmou a tela de ensaio. A causa dessa ocorrência inicial não foi confirmada; não declarar uma correção de código para ela.

Em seguida, o operador executou o teste sintético e confirmou explicitamente: “Swift -> Hermes, 121 frames, Teste sintético: PASS”. Essa é evidência de execução no aparelho, observada pelo operador; os logs CLI não registraram a linha `SilentVoiceLab synthetic`.

O operador autorizou a câmera pelo controle explícito e confirmou a captura com prévia frontal: 121 frames, zero perdas reportadas, 4.000 s, 30 FPS, 480 × 640, BGRA32, orientação portrait e espelhamento false. A mensagem de normalização BGR8/inferência indisponíveis permaneceu visível.

O operador confirmou cancelamento manual com encerramento da câmera (indicador verde apagou), cancelamento ao ir para background com possibilidade de iniciar outra captura ao retornar e retorno ao fluxo normal pelo botão do laboratório com a câmera desligada. Nenhuma equivalência de pixels ou inferência foi alegada.

Decisões: preservar o contrato recebido; manter formatos reais incompatíveis bloqueados; usar dados sintéticos no caminho nativo sem chamar câmera; não instalar dependências npm nem alterar a arquitetura USB. Nenhum commit, push ou publicação.
