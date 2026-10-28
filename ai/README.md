# Núcleo de reconhecimento — João

Este diretório é o ponto de entrada para o núcleo que combina os sinais do dispositivo para reconhecer palavras. Ele **não** é o chatbot comercial da landing, que continua em `apps/api/src/chat`.

O código do núcleo ainda não foi fornecido. Não há linguagem, framework, modelo ou comando de execução escolhido artificialmente nesta migração.

## Primeira contribuição

1. Crie uma branch a partir de `main` do monorepo.
2. Adicione o código em `ai/`, com manifesto e lockfile do ecossistema realmente usado.
3. Documente versão do runtime, instalação, execução, inferência e testes reproduzíveis.
4. Defina entradas/saídas, unidades, erros, versionamento e fixtures sintéticas com a equipe antes de integrar API/mobile/hardware. Os contratos web existentes não substituem um protocolo de reconhecimento.
5. Abra PR com um exemplo mínimo e testes que não dependam de dados privados. A revisão é encaminhada ao João e ao mantenedor.

## Dados e artefatos

Não versionar datasets, gravações reais, identificação de participantes, pesos ou checkpoints no Git comum. Use armazenamento separado com acesso definido e documente a origem/licença/consentimento e como obter o material de forma autorizada. `datasets/`, `artifacts/` e `runs/` são ignorados. Pequenas fixtures sintéticas podem ficar em `tests/fixtures/`, revisadas para não conter dados pessoais.

A interface física continua sendo MyoWare 2 → ESP32-S3 → Raspberry Pi Zero 2 W → USB → Android. O protocolo USB ainda não foi definido. Esta organização não autoriza mudar o transporte nem implementar um driver no app.
