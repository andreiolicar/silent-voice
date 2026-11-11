# Ensaio horizontal BGR8

Continuação do [ensaio de captura frontal](ios-front-capture.md). O operador aprovou testar primeiro na horizontal para preservar a entrada 4:3 exigida pelo Python. A orientação final do produto não foi definida por esse ensaio.

## O que é convertido

`BGR8Converter.pack` lê um buffer BGRA32, respeita `bytesPerRow` e produz B, G e R compactados em ordem row-major. Não há crop, resize, interpolação, troca espacial de pixels ou transformação de colorimetria. Os limites aceitam no máximo 307.200 pixels; buffers, dimensões e stride inválidos são rejeitados.

Na captura real convertida, a origem precisa ser BGRA32 640 × 480, não planar e não espelhada, com configuração de aquisição horizontal. O código bloqueia retrato/posição indeterminada antes da câmera e cancela se a orientação física mudar. O buffer BGR de 921.600 bytes existe somente no callback nativo e é descartado. JavaScript recebe apenas metadados de origem/conversão; não recebe imagens, hashes ou amostras de uma pessoa.

A correspondência entre UIDevice e AVCapture inverte os nomes landscapeLeft/landscapeRight. O rótulo `upright` do buffer convertido deriva da configuração de aquisição e da orientação física mantida; não é uma verificação facial.

O ensaio de origem em retrato continua disponível e não passa a ser convertido implicitamente. O gate congelado só recebe metadados BGR8 depois de conversão bem-sucedida. Resultado técnico PASS não executa inferência.

## Referência sintética independente

O gerador em `modules/silent-voice-capture/fixtures/generate_bgr8_reference.py` usa somente Python padrão. Gera um padrão BGRA aritmético com alfa variável e 16 bytes de padding por linha. O esperado BGR é construído independentemente, sem executar o conversor Swift.

- Dimensões: 640 × 480.
- Stride BGRA sintético: 2.576 bytes.
- Saída BGR: 921.600 bytes.
- SHA-256 esperado: `94886147b68e9d9c9358ad52b2a3f8ccc99da1a5c01881e0466c6fceb217f00a`.
- Fixture: `src/features/visual-recognition/data/bgr8-reference.json`, com amostras de pixels e metadados, sem imagem/dado pessoal.

Para reproduzir, na raiz do monorepo, escolha uma saída nova. O gerador recusa sobrescrita:

```sh
python3 apps/mobile/modules/silent-voice-capture/fixtures/generate_bgr8_reference.py --output /tmp/bgr8-reference-nova.json
swift test --package-path apps/mobile/modules/silent-voice-capture
npm test --workspace @silent-voice/mobile
```

Os testes Swift carregam a fixture canônica pelo caminho de fonte do monorepo. O módulo instalado gera sua entrada sintética em memória; o Hermes compara seu resultado com a referência Python incluída na build. Somente essa entrada sintética produz hash/amostras.

## Controles no aparelho

Na build privada de laboratório:

1. Executar o teste temporal anterior e “Testar conversão BGR8 sintética”. Esperado: ambos PASS.
2. Em retrato, tocar em “Capturar BGR8 horizontal”. Esperado: orientação bloqueada e câmera não iniciada.
3. Segurar o telefone horizontalmente e capturar por quatro segundos. Repetir com o outro lado. Registrar origem, convertido, bytes/frame, FPS, perdas e gate técnico.
4. Durante outra captura BGR8, girar para retrato. Esperado: cancelamento/câmera encerrada.
5. Conferir cancelamento manual e background/nova tentativa. Voltar ao fluxo normal.

A UI permanece em retrato nesta build técnica. Nenhuma alteração global de orientação ou autenticação foi introduzida.

## Limites

A igualdade sintética verifica empacotamento de canais/linhas. Não demonstra igualdade entre sensores, decodificadores, corimetria, landmarks, ROI, tensor, DTW ou inferência R4. Os pesos e dados privados continuam fora desta entrega; seus direitos e compartilhamento permanecem pendentes. Nenhum threshold foi alterado.

## Resultado da execução

Oito testes Swift passaram, incluindo hash/amostras Python exatos e casos de padding, alfa, truncamento, overflow e orientação. A suíte raiz passou com 50 testes mobile e três testes PostgreSQL ignorados pela configuração existente; tipos, lint/formatação e build passaram. Expo Doctor/install check mantêm os seis desalinhamentos de patch anteriores, sem upgrades.

Build iOS Release compilada, assinatura validada e instalação/abertura confirmadas por devicectl. O operador executou os dois testes sintéticos no iPhone e confirmou PASS no temporal Swift/Hermes e na conversão BGR8 contra a referência Python.

O operador também confirmou bloqueio em retrato sem abrir a câmera e a primeira captura horizontal com estes valores:

| Medida                              | Observação do operador |
| ----------------------------------- | ---------------------- |
| Frames / perdas reportadas          | 121 / 0                |
| Duração / FPS                       | 4.000 s / 30.00        |
| Origem                              | 640 × 480, BGRA32      |
| Bytes da origem / stride            | 1.228.864 / 2.560      |
| Convertido                          | 640 × 480, BGR8        |
| Bytes convertidos por frame         | 921.600                |
| Orientação declarada / espelhamento | upright / false        |
| Gate técnico                        | PASS                   |
| Reconhecimento                      | Indisponível           |

O operador repetiu a captura na outra posição horizontal e confirmou o mesmo formato convertido, 921.600 bytes/frame e gate PASS. Também iniciou BGR8 e girou para retrato antes de quatro segundos: confirmou cancelamento e encerramento da câmera.

Na conferência final, o operador confirmou a preservação do ensaio de origem em retrato (BGRA32, 480 × 640, gate BLOCKED), cancelamento manual do modo BGR8 com câmera encerrada, cancelamento ao ir para background com nova captura disponível ao retornar e retorno ao fluxo normal do aplicativo com câmera desligada.

A revisão independente não encontrou defeito funcional bloqueante. A ausência inicial de bytes/stride de origem foi corrigida para cumprir a spec, com teste de regressão observado falhando e depois passando. Os valores reais da origem permanecem separados do buffer convertido. Nenhum commit, push ou publicação foi realizado; alterações locais preservadas em `codex/ios-device-build`.

Esses números demonstram o ensaio de formato/cadência com conversão ativa; não demonstram equivalência R4 ou reconhecimento.
