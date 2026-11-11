# Contrato visual preliminar — IOS-HANDOFF-02.4

O contrato de preparação do João está em `src/features/visual-recognition/contract.ts`. Ele valida metadados e cadência de uma captura sintética. Não adquire frames, transforma pixels, detecta rostos ou executa modelos. `startGlobalRecognition` sempre retorna `model-unavailable`, inclusive se o chamador informar `available: true`.

## Execução

Na raiz do monorepo:

```sh
npm test --workspace @silent-voice/mobile
```

O comando existente inclui os dez casos de contrato recebidos, o caso de comparação temporal com a fixture Python e dois casos adicionais: capturas vazias/incompletas e flag de disponibilidade sem implementação.

Os timestamps do contrato são nanosegundos inteiros relativos ao primeiro frame. Um futuro adaptador deve subtrair a origem na precisão inteira nativa antes de converter para `number`. O gate espera metadados de frames 640 × 480, BGR8, orientação upright e `mirrored: false`; esses metadados não comprovam o conteúdo de um buffer de pixels.

## Proveniência

Pacote recebido: `ios-handoff-02.4-parcial.zip`.

SHA-256 do ZIP: `addd0dcf998c3ad8cccb78ec39234e3d043c83d87b5fb5cd2a3c71a5b4e4fb5f`.

Hashes dos arquivos originais, conferidos antes da incorporação:

| Arquivo no pacote                                                  | SHA-256 original                                                   |
| ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `contract/apps/mobile/src/features/visual-recognition/contract.ts` | `c99fef68187508bdd1247e91a749f5dc8048150034cefd40c62bc5f87a8853bc` |
| `contract/apps/mobile/tests/visual-recognition.test.mjs`           | `49b9a46bb8a0326b08d0ac0c6f96d2b3ef35eac2778227f0984b0ac71839df26` |
| `synthetic/check_temporal_fixture.mjs`                             | `4fd3ba9b1ac74dbab8d1008059de36663555635e70cb3d334293b10c35e0e02f` |
| `synthetic/fixtures.json`                                          | `69bb1188c3f2cd75495b23fd5c3bf133c1da5d2fe21eac361fc3177416eeff5a` |

O contrato foi preservado byte a byte, incluindo seu hash original. O teste temporal teve os caminhos ajustados e a formatação normalizada, e o teste de contrato recebeu os dois casos adicionais. A fixture foi movida para `tests/fixtures/visual-recognition.json` e reformatada, com todos os valores preservados. Os hashes acima identificam a origem dos arquivos.

## Limites de validação

O único estágio comparado com a referência Python nesta suíte é o gate temporal da entrada sintética fornecida. A fixture também contém valores de segmentação, tensor e DTW para trabalho futuro; eles não têm implementação TypeScript nem comparação nesta integração. O gerador Python não foi incorporado nem reexecutado.

Testes Node não demonstram execução em Hermes/iPhone, equivalência numérica nativa ou reconhecimento GLOBAL. O ciclo posterior adicionou uma [área privada de ensaio](ios-front-capture.md), que consome este contrato para teste sintético e diagnóstico. No iPhone, o operador confirmou o teste temporal Swift → Hermes com 121 frames e resultado PASS. O [ensaio BGR8 posterior](ios-bgr8.md) acrescentou comparação sintética exata do empacotamento de bytes e aquisição horizontal com conversão/gate técnico. Isso não valida FaceMesh, ROI, normalização do tensor nem R4 real, que continuam dependentes de outros testes e das liberações pendentes.

O contrato permanece separado de `SilentVoiceDevice`, que representa o caminho USB/Raspberry. A captura de câmera do iPhone não foi adicionada neste incremento.
