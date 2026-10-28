# Núcleo de reconhecimento — João

Este diretório é o ponto de entrada para o núcleo que combina os sinais do dispositivo para reconhecer palavras. Ele **não** é o chatbot comercial da landing, que continua em `apps/api/src/chat`.

O núcleo Python experimental inclui os modos GLOBAL e PERSONALIZED do Live Tester C4.4. A instalação do código, a disponibilidade privada dos artefatos R4 e a validação operacional são etapas distintas.

## Primeira contribuição

1. Crie uma branch a partir de `main` do monorepo.
2. Adicione o código em `ai/`, com manifesto e lockfile do ecossistema realmente usado.
3. Documente versão do runtime, instalação, execução, inferência e testes reproduzíveis.
4. Defina entradas/saídas, unidades, erros, versionamento e fixtures sintéticas com a equipe antes de integrar API/mobile/hardware. Os contratos web existentes não substituem um protocolo de reconhecimento.
5. Abra PR com um exemplo mínimo e testes que não dependam de dados privados. A revisão é encaminhada ao João e ao mantenedor.

## Dados e artefatos

Não versionar datasets, gravações reais, identificação de participantes, pesos ou checkpoints no Git comum. Use armazenamento separado com acesso definido e documente a origem/licença/consentimento e como obter o material de forma autorizada. `datasets/`, `artifacts/` e `runs/` são ignorados. Pequenas fixtures sintéticas podem ficar em `tests/fixtures/`, revisadas para não conter dados pessoais.

A interface física continua sendo MyoWare 2 → ESP32-S3 → Raspberry Pi Zero 2 W → USB → Android. O protocolo USB ainda não foi definido. Esta organização não autoriza mudar o transporte nem implementar um driver no app.

## Execução local da IA

Em `ai/`, com Python 3.12.10 e autorização para instalar dependências:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[live-tester,dev]"
.\.venv\Scripts\python.exe -m scripts.demo.global_live_visual_tester --visual-preview
.\.venv\Scripts\python.exe -m pytest tests -q
```

A prévia é sintética, não testa câmera nem inferência. O runtime exige os artefatos R4 e os manifestos privados originais nos caminhos documentados em `docs/c44_live_tester_reproducibility.md`. Obtenha-os somente de armazenamento autorizado, respeitando licença, consentimento e controle de acesso. Não adicione os arquivos ao Git. A ausência ou divergência bloqueia a verificação operacional; não contorne as verificações. Áudio contextual requer o extra `audio` e checkpoint local autorizado.

O teste público cobre o recorte migrado; não reproduz a regressão histórica completa. A instalação em máquina limpa e a integração com app ou hardware não foram validadas. O manifesto de migração local está em `docs/public_migration_manifest.md`.
