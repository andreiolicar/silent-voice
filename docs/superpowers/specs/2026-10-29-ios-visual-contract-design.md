# Preparação do contrato visual iOS

O próximo incremento incorpora ao monorepo os contratos e testes sintéticos já entregues por João no IOS-HANDOFF-02.4. A primeira build do aplicativo abriu no iPhone; o reconhecimento real continua indisponível.

## Escopo

- Adotar `CapturedFrame`, `VisualState`, `CaptureResult`, `relativeCaptureTimestampNs`, `analyzeCapture` e `startGlobalRecognition` no caminho proposto pelo pacote: `apps/mobile/src/features/visual-recognition/contract.ts`.
- Executar os dez testes de contrato e o teste temporal de referência pelo comando de testes mobile existente.
- Preservar a fixture sintética original e registrar sua origem e seus limites.
- Verificar também que um sinalizador `available: true` sozinho não habilita reconhecimento e que capturas vazias/incompletas são bloqueadas.

## Abordagem

Incorporar o módulo independente de plataforma e os testes é a opção escolhida para esta continuação: aproveita o contrato recebido sem decidir um novo runtime. Manter os arquivos somente no ZIP deixaria a preparação fora da regressão do aplicativo. Ligar agora a câmera ou substituir o fluxo Live exigiria outro incremento de arquitetura e validação nativa.

O módulo não será conectado às telas nesta etapa. A arquitetura USB/Raspberry, a autenticação e a experiência atual permanecem como estão. Não adicionar dependências, modelos, dados pessoais, captura, armazenamento de frames, ONNX ou MediaPipe.

## Critério de aceite

Os testes recebidos executam no workspace mobile e na suíte raiz. Typecheck, lint, formatação e build existentes passam. Os testes em Node demonstram apenas o contrato TypeScript e o caso temporal sintético; não demonstram execução do módulo no Hermes/iPhone, equivalência de pré-processamento, segmentação, tensor, DTW ou inferência.

Nenhum commit, push ou publicação. Reutilizar a branch local de preparação existente e preservar suas alterações.
