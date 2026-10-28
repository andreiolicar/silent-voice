# C4.4 — instalação e proveniência do Live Tester

O Live Tester é experimental. Instalar o código, disponibilizar os artefatos
R4 e comprovar a operação com câmera são etapas distintas. A instalação por
si só não comprova captura válida, reconhecimento ou desempenho.

## Instalação em Windows

Usar Python 3.12.10 na criação de `.venv`, na raiz do repositório. Em ambiente
novo e com autorização para instalar os pacotes:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[live-tester]"
```

O grupo `live-tester` fixa Pillow 12.3.0, ONNX Runtime 1.30.0, PyTorch
2.14.0 e SciPy 1.17.1. NumPy 1.26.4, MediaPipe 0.10.21 e OpenCV contrib
4.10.0.84 são dependências do projeto. O runtime exige `CPUExecutionProvider`.
Para áudio contextual e Whisper, instalar também `-e ".[live-tester,audio]"`;
essa opção inclui SoundDevice e OpenAI Whisper. Um checkpoint Whisper local
compatível deve ser disponibilizado separadamente. A IA contextual remota é
opcional, depende de credenciais e só é ativada por ação explícita na sessão.
Nenhum modelo é baixado automaticamente por estas instruções.

Após instalar os 12 arquivos C4.4 e suas dependências, a prévia sintética é:

```powershell
.\.venv\Scripts\python.exe -m scripts.demo.global_live_visual_tester --visual-preview
```

A prévia não abre câmera ou modelos e não prova inferência. Para uma sessão
operacional supervisionada, a documentação da interface explica seleção de
câmera e controles; os artefatos abaixo devem estar disponíveis antes da
inferência. Condições locais de câmera, FPS e acesso são verificadas na sessão.

## Artefatos de inferência R4

Obter os arquivos congelados de armazenamento local autorizado do projeto;
não regenerar, treinar, recalibrar ou substituir por dados de held-out. Os
arquivos abaixo permanecem ignorados pelo Git. Seus bytes devem corresponder:

| Caminho relativo | SHA-256 |
| --- | --- |
| `data/processed/models/edge/cycle_06_swinlip_clip_encoder_fp16.onnx` | `ff81172639263a6a74975e7147d63e62af944b947e48f53fba6980af732c91a7` |
| `data/processed/models/edge/cycle_06_positive_head_fp32.onnx` | `eb299d65e4f2b9a15108f79b8044355068911d2180161d46806a9c0269fa9261` |
| `data/processed/models/rejection_4/rejection_4_top3_policy.onnx` | `28b214850ce53fdcb7170c0fab52620cf8a6c97c2be712092686658b81d5169f` |
| `data/processed/models/rejection_4/rejection_4_top3_reference_bank.npz` | `e0fefb568ee3f689c75354cd1c75696d7cef91e215bd7cb3a99039ecf092a34c` |
| `data/processed/models/cycle_06_hybrid_positive_classifier.pt` | `33a0d1f1f564dc75f83ebc08fc2dca255840da60ca40a9c41fdd36d4ad0cc6a2` |
| `data/processed/evaluation/cycle_06_positive_classifier_final_config.json` | `29b7df189ac8f3b5b01ce2b5b5b03870dd37b678ccb6f6f536e8ac9debaa7a1e` |
| `data/processed/evaluation/cycle_06_edge_preheldout_final_config.json` | `a761de851e7dc22ed8974dbd3dc98e23963d384057488bdfe9aae0ef406eb4d4` |
| `data/processed/models/edge/cycle_06_onnx_fp16_rejection_clip_centroids.npz` | `d7cece625425d09cb313830e0491121b42d116f409bd400bf9c18f7ea53e0a61` |
| `data/processed/evaluation/cycle_06_preheldout_freeze_manifest.json` | `41cf1f308a1c153bfc0f533c70676309139d63531cce9ce31363c74643e611bd` |

Os manifests e freezes versionados também são exigidos. O inventário completo
é a allowlist `LIVE_PROVENANCE_NAMES` e `PROVENANCE` no runtime; a verificação
abaixo confere seus hashes, os artefatos acima e a configuração ONNX CPU, sem
abrir câmera, executar inferência ou ler o resultado held-out consumido:

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; from silent_voice.inference.live_visual_tester import verify_frozen_sources; verify_frozen_sources(Path.cwd()); print('Proveniência R4 verificada')"
```

Qualquer ausência ou divergência bloqueia a execução. Não adicionar ao Git
artefatos, dados pessoais, exemplos de enrollment, perfis ou logs.

## Limites dos testes

A regressão usa o scorer congelado local como pré-requisito de um preflight de
integração. O teste documental com head pessoal real é integração e registra
SKIP se o head não está disponível. As integrações com o preflight MSV e
com os metadados pessoais históricos registram SKIP se os arquivos necessários
não estão disponíveis. Há testes sintéticos separados para esses contratos, o
bloqueio por tentativa prévia e divergência do hash do head. Os dois testes de
segurança com symlink real permanecem preservados; em Windows sem privilégio
eles registram SKIP, não PASS. O diagnóstico DEV-04 documentou abertura e
encerramento da janela no VS Code; ele não estabeleceu desempenho nem garante
a cadência da câmera em outra máquina.
