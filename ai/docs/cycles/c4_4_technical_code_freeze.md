# C4.4 — congelamento técnico do código do Live Tester

## Estado e limites

Estado: `TECHNICAL_CODE_FROZEN`.

Este registro identifica os bytes de trabalho aprovados na C4.4-FREEZE-05,
antes de sua inclusão em commits. O HEAD de referência é
`eb2c348d4ae917b266f41cda8841ffc234840610`, branch `main`; o HEAD isoladamente
não contém os arquivos não rastreados ou alterações de trabalho listadas aqui.
Os SHA-256 abaixo são de arquivos de trabalho, não de blobs Git. Preservar as
regras de materialização e conferir os hashes antes de qualquer incorporação.

O estado significa congelamento técnico do código inventariado. Não representa
aprovação científica, validação de novos usuários, comprovação de desempenho de
produto ou liberação completa da integração. Não autoriza alterar modelos,
thresholds, rejection ou policy temporal. Instalação do código, disponibilidade
dos artefatos e validação operacional são etapas distintas.

## Manifesto dos 12 arquivos C4.4

| Arquivo | SHA-256 |
| --- | --- |
| `docs/global_live_visual_tester.md` | `42afd51c9ee21e547c98f20d3e3917abcc8519de0797e3e6854a43ca7937e381` |
| `scripts/demo/global_live_visual_tester.py` | `f892a9da70b055fa7fb746543600183ed8a17e08347404a6cb3b4dd8eafb2259` |
| `src/silent_voice/inference/global_live_visual_tester.py` | `5dd3d2bf7578ef94b11f67b46178a759bc4341c4d9bddcfce8c03c35e75dd1ae` |
| `src/silent_voice/inference/global_live_visual_tester_window.py` | `e74295a64e465dffa8005e0c2863badc177b10abfe3e342f3023b86928a4a0d3` |
| `src/silent_voice/inference/personal_live_visual_tester.py` | `5e96dae6c2b8938c989edb5e065f6a9f7d18b32fe03e7eaf9a5e8cee715343a9` |
| `src/silent_voice/inference/live_context_session.py` | `73f70a468be1755502c873daecd267541e5aeecdc65900228f42973b6efcaeae` |
| `src/silent_voice/inference/live_fps_diagnostic.py` | `fd2521fcd2d90557d77d6e83ccf60977b7bfc4c7fbce55a69fb7c5ced47e5d12` |
| `src/silent_voice/inference/live_visual_tester.py` | `f9ec0592c4171646e99eefc2194d28bfe3b1ea0b3b49ec5c1ba9893b0ec0615e` |
| `tests/unit/inference/test_global_live_visual_tester.py` | `47eb7407e96dda4ab6ca677e976a3a7324e459932c9a3f33cf7ab144a65176a2` |
| `tests/unit/inference/test_personal_live_visual_tester.py` | `dd30519ccce8ea9baaea3b5c06781959b6030b431032d6ae5cefc48c30313c31` |
| `tests/unit/inference/test_live_context_session.py` | `906c2db38bd94070aa8d88a74141a179a33044822ee215021da5d28f002b1608` |
| `tests/unit/inference/test_live_visual_tester.py` | `3e5dc01b33ab68b90fbeac0fcad34075955e2dccace016d2d4f9005e5cc02313` |

## Remediação de reprodutibilidade

As sete correções incorporadas e validadas na FREEZE-05 são:

| Arquivo | Finalidade | SHA-256 |
| --- | --- | --- |
| `.gitattributes` | Materialização específica dos dois documentos congelados | `c2a868f2be0857d38bfcdf9fdbb8f9f308ae9cff32ea5258259a6ca47b77831c` |
| `pyproject.toml` | Extra explícito `live-tester` | `fbe1f9beccc02068a4256d4a03d2322404ec8e5e6be071fcae85d58dca44bc78` |
| `tests/unit/vision/test_msv_v2_new_sessions.py` | Fontes históricas sintéticas e integração real preservada | `617a35e12222bf7976ba0bc2314511528224e70f04b077f767055f140c7885c5` |
| `tests/unit/vision/test_personalized_rejection_01_protocol.py` | Gates sintéticos e integração com head real preservada | `a3bbbdf01c7109c0b1079704a56aa65a8199afe88e12be21ff9e32268b47be31` |
| `tests/unit/vision/test_visual_personalization_feature_build.py` | Gate sintético e integração histórica preservada | `dcac5d569694ff2c63a453c9d4bf3dd8f852081c2fd603071d3e1f908dae8503` |
| `tests/unit/test_c44_reproducibility.py` | Contratos de atributos, hashes e dependências | `d93d619cb6326ba71656c07f08e9bddd9875514617a02b1ed3b8be005fd7c52b` |
| `docs/c44_live_tester_reproducibility.md` | Instalação, proveniência e limites | `00f16338a3af2fdbe7b75851d4062a61dc5e8a7081a3f598d1267f9b97dbef44` |

A policy temporal v2 permanece com SHA-256 de arquivo
`4680a3fb47866d470fb98223c8f8d654d19150905d4ba7289096e80d8a6f39a1`.
A resolução histórica GV2.9 permanece com SHA-256 de arquivo
`ed13ca983c2814822fbc65ac16142ab365b1e281d0eff2b96d4efb1fc8d483bf`.
A prova de materialização com `core.autocrlf=true` reproduziu ambos os hashes.
Nenhum conteúdo científico foi alterado para obter esses valores.

## Correções GV2.9 — escopo separado

As duas alterações preexistentes são um pré-requisito de compatibilidade da
regressão e pertencem a commit separado; não integram os 12 arquivos C4.4:

| Arquivo | SHA-256 |
| --- | --- |
| `tests/unit/vision/test_global_v2_gv29_fix2e.py` | `cf923ad682580b6b763f722e336a75ac5b93c0960ed653c6a16a2df61b4b6386` |
| `tests/unit/vision/test_global_v2_source_allowlist.py` | `d23525a79d371ad87be52496df002ed54a87c0a96978321e027b8803b0e0d8b0` |

Os testes de agregação usam resultados sintéticos; os testes de segurança com
symlink real foram preservados, assim como testes portáveis de bloqueio antes
da abertura.

## Validação de código

Na FREEZE-05, após incorporação controlada ao checkout principal:

- Testes direcionados: **309 PASS / 0 FAIL / 2 SKIP**, dois warnings.
- Regressão completa: **3.154 PASS / 0 FAIL / 2 SKIP**, dez warnings.
- Black, Flake8 e `git diff --check`: PASS; Black não alterou arquivos.
- Os três testes de integração histórica foram executados porque seus
  pré-requisitos estavam presentes no checkout principal.
- Os dois SKIP são `test_fix1_symlink_authorized_path_to_heldout_blocked_before_open`
  e `test_fix1_symlinked_directory_component_blocked_before_open`, em
  `tests/unit/vision/test_global_v2_source_allowlist.py`: Windows sem privilégio
  para criar symlink real (`WinError 1314`). Não foram declarados PASS.

Os dez warnings da regressão consistem em dois `DeprecationWarning` de tipos
`google._upb`/Python 3.14, dois avisos do exportador ONNX legado do PyTorch,
dois avisos de depreciação de logging desse exportador e quatro `TracerWarning`
por conversão de tensores em booleanos no teste de exportação. O Git também
avisou sobre possível conversão LF/CRLF futura em arquivos de trabalho;
`git diff --check` terminou sem erro. A validação não estabelece desempenho de
inferência em novos usuários ou em hardware final.

## Evidência operacional e limitações

- **DEV-01:** 14 tentativas GLOBAL, incluindo dois controles UNKNOWN. Duas
  tentativas têm desvios relatados pelo operador: duas articulações na mesma
  janela e uma janela sem articulação. O relatório é `DEV_OPERATIONAL_ONLY`.
  Plano SHA-256 `014bc6c1e2bb1842be8a925636dc02b9577a7ca3ad1bc4969cd35c959a33efa2`;
  relatório SHA-256 `0a02921be239d034ea8f746f9c1e5a9a2a5bc48814d790a240a9567838f07050`.
- **DEV-02:** 12 exemplos de enrollment TWO-SHOT e 14 tentativas primárias
  PERSONALIZED, com duas tentativas adicionais de SIM expressamente
  exploratórias e excluídas da comparação primária. O relatório v2 corrige a
  associação do controle OOV e preserva referência à versão anterior. Os
  resultados são `EXPLORATORY_OPERATIONAL_ONLY`; não são estimativa de
  generalização. Plano SHA-256
  `23b2338660eee0553f06dd22af0231087fd3700550e7b4462bbd6d888dbb7af9`;
  relatório v2 SHA-256
  `259e0951bf28d70ec2595a2dd82ff8c90220b6afe37e404d3007900660a7d46a`.
  O processo de captura precisou de interrupção no terminal após a janela ter
  informado fechamento. Os logs e perfis permanecem locais e fora do Git.
- **DEV-04:** `OPERATIONAL_PASS` para abertura e encerramento supervisionados
  no terminal integrado do VS Code: índice 1 identificado como iPhone/Iriun,
  índice 0 como câmera integrada; X e ESC retornaram código 0. Não houve
  captura de palavras nessa validação. O registro está na sessão operacional;
  não existe aqui um relatório versionado independente para essa observação.

Os dados DEV-01/02 são pequenos, de um participante e operacionais; o
same-speaker de desenvolvimento não é usuário inédito. Os diagnósticos de
cadência disponíveis incluem bloqueios por FPS insuficiente; a origem não foi
demonstrada. DEV-04 não comprova cadência ou generalização em outro ambiente.

## Instalação e dependências externas

O extra `live-tester` declara Pillow 12.3.0, ONNX Runtime 1.30.0, PyTorch
2.14.0 e SciPy 1.17.1. NumPy 1.26.4, MediaPipe 0.10.21 e OpenCV contrib
4.10.0.84 constam nas dependências principais; áudio contextual e Whisper
usam o extra `audio` e checkpoint local separado. O R4 exige CPUExecutionProvider
e os artefatos congelados de encoder, head, scorer, banco e proveniência.
O inventário de caminhos, hashes e o procedimento de verificação estão em
[`docs/c44_live_tester_reproducibility.md`](../c44_live_tester_reproducibility.md).
A disponibilidade desses artefatos não implica validação operacional. O
resolvedor foi verificado offline sobre a virtualenv existente; **não houve
instalação nem validação em máquina limpa**.

## Exclusões e manifesto de commits recomendado

Não incluir no Git modelos, dados pessoais, vídeos, exemplos de enrollment,
perfis, logs, datasets ou artefatos da investigação OV5647. Também ficam fora
as alterações de demonstração remota e outros trabalhos preexistentes não
listados neste registro. Nenhum estágio, commit, push ou merge foi realizado
pela criação deste documento.

A sequência proposta para aprovação posterior é:

1. `test: preserve Windows symlink security coverage` — os dois arquivos GV2.9
   listados no escopo separado.
2. `test: isolate historical preflight coverage` — os três testes de MSV e
   personalização da tabela de remediação.
3. `build: make live tester setup reproducible` — `.gitattributes`,
   `pyproject.toml`, `tests/unit/test_c44_reproducibility.py` e
   `docs/c44_live_tester_reproducibility.md`.
4. `feat: add global and personalized live visual tester` — os 12 arquivos
   C4.4 e este registro `docs/cycles/c4_4_technical_code_freeze.md`.

O escopo de cada commit deve ser revisado novamente antes de qualquer estágio;
os grupos 2 e 3 dependem conjuntamente das correções de reprodução e devem ser
validados no conjunto antes da integração final.
