# Paridade numérica sintética no iPhone — proposta anterior

**Substituída em 30/10/2026:** Andrei solicitou integração integral de GLOBAL, PERSONALIZED e áudio/contexto, com solicitação das dependências faltantes ao João. Este ciclo isolado não foi aprovado. O escopo atualizado está em [IOS-HANDOFF-03](2026-10-30-ios-complete-core-handoff-request.md); preservar estes critérios como material técnico para a integração completa, sem tratá-los como autorização separada de implementação.

## Intenção e estado

A captura frontal e o empacotamento horizontal BGR8 já foram ensaiados no iPhone. A próxima entrega proposta valida os cálculos públicos que podem ser executados sem pesos, câmera ou dados pessoais. Esta proposta ainda aguarda aprovação de Andrei; não autoriza inferência R4 real.

## Abordagens

1. **Recomendada: cálculos nativos com entradas sintéticas.** Portar segmentação, seleção de 29 índices, formação do tensor e DTW para o núcleo Swift existente. Comparar com a referência Python entregue por João, inclusive no iPhone. Reduz as lacunas numéricas antes de introduzir detector/runtime.
2. **Detector facial primeiro.** Requer decidir e validar a compatibilidade do detector com o MediaPipe Python congelado, além da disponibilidade e das condições dos seus artefatos. Não resolve por si só a paridade dos cálculos posteriores. Fica para uma decisão separada.

A recomendação é técnica do implementador, ainda não uma escolha atribuída ao operador. Não serão instalados NumPy, Torch, MediaPipe ou ONNX Runtime neste ciclo.

## Fontes e referência

- `ai/src/silent_voice/vision/visual_activity_segmentation.py` e `visual_experiment_defaults.py`.
- `ai/src/silent_voice/vision/swinlip_frozen_encoder.py`: apenas `select_source_frame_indices` e `prepare_input`; sem carregar o encoder.
- `ai/src/silent_voice/vision/strong_dtw_distance.py`.
- Fixture canônica já recebida em `apps/mobile/tests/fixtures/visual-recognition.json` e gerador `synthetic/generate_fixtures.py` dentro do ZIP IOS-HANDOFF-02.4.
- O gerador recebido será preservado como evidência/proveniência. Os resultados recebidos são uma referência entregue pelo João, não uma nova execução Python no Mac. Não alegar regeneração sem executá-la.
- Integração reaproveita o módulo local existente e o Expo SDK 57: https://docs.expo.dev/versions/v57.0.0/.

## Entrega

### Segmentação e seleção temporal

Implementar funções puras Swift limitadas a 256 frames e 160 features por frame, com rejeição de formas inconsistentes, valores não finitos e configuração inválida. Esses limites protegem este adaptador; não são alteração dos thresholds do R4.

Preservar a configuração recebida: início das velocidades 80, janela 5, razão 0.25, padding 6, mínimo 18 frames e faixa mínima 1e-6. Calcular atividade RMS em Double, suavização com zeros nas bordas conforme `np.convolve(..., mode='same')`, percentil 20 com interpolação linear, comparação estrita `>` e fallback para a sequência completa. Preservar expansão mínima e intervalo com fim exclusivo.

Selecionar 29 posições entre início e fim inclusivo, equivalentes a `np.rint(np.linspace(start,end_exclusive-1,29))`, incluindo arredondamento de empates para o inteiro par. Não substituir por interpolação de features nem por timestamps. Aceitar repetições para segmentos curtos, como faz o Python.

Caso recebido: matriz Float32 40 × 160 com valores 1 apenas em `[10,26) × [80,160)`. Esperado: detectado, intervalo `[3,33)` e os 29 índices exatos da fixture.

### Tensor sintético

Consumir ROIs grayscale UInt8 96 × 96 já fornecidas à função pura; **a geração dessas ROIs a partir da câmera não faz parte desta entrega**. Selecionar os índices, aplicar o recorte central `[4:92,4:92]` e formar Float32 contíguo B,C,T,H,W = 1,1,29,88,88, com operações separadas `(pixel/255 - 0.421)/0.165` na precisão usada pela referência. Esse recorte é do tensor de ROIs e não muda a aquisição BGR8 da câmera.

Entrada sintética aritmética: `(t + 3*y + 7*x) % 256`, 40 × 96 × 96. Comparar shape, dtype, amostras e SHA-256 dos bytes Float32 little-endian com `dac7f2a27de50fa633b0a0d06bf50657efed810a890e642be7698007b2cce105`. Uma divergência de hash bloqueia o PASS; não adotar tolerância nem modificar o esperado para acomodar a implementação.

### DTW

Portar a distância pública: norma euclidiana em Double, programação dinâmica em duas linhas e desempate por custo e depois menor comprimento, preservando a ordem diagonal/vertical/horizontal quando ambos empatam. Suportar normalização por comprimento e limite de warping conforme a fonte, validar entradas e tratar alinhamento impossível como erro. Limites deste adaptador: até 256 frames por sequência e 160 features.

Caso recebido: `[[0],[1],[2]]` versus `[[0],[2]]`, sem normalização/limite: distância 1 e comprimento 3. Isso não cria um classificador nem compara templates privados.

### Ensaio na build privada

Adicionar um comando explícito na área de ensaio para executar os três estágios com entradas geradas no Swift. Hermes compara os resultados com as seções correspondentes da fixture recebida. Manter uma única fonte de valores esperados acessível aos testes e ao bundle; eventual movimentação da fixture deve preservar todos os valores e atualizar o teste temporal existente.

Exibir PASS/FAIL por estágio e resumo único. Nunca devolver PASS fixo nem usar o esperado como resultado do cálculo. Retornar apenas metadados, índices e diagnósticos sintéticos pequenos; nenhum tensor completo cruza a ponte. Não abrir câmera, solicitar permissões, acessar arquivos privados ou habilitar reconhecimento. Cancelar/ignorar atualização tardia da tela após perda de foco/background, reutilizando o mecanismo atual.

Preservar todos os comandos de captura, cancelamento, retorno ao fluxo normal, guards de autenticação e o contrato congelado do João. Sem novos pacotes ou upgrades.

## Critérios de aceite

- Testes Swift contra a fixture recebida e casos pequenos calculáveis independentemente: silêncio/fallback, atividade nas bordas, expansão mínima, percentil, janela maior que a sequência, arredondamento par, segmento de um frame, entradas inválidas, índices e ordem espacial do tensor, DTW com empate/normalização/warping impossível.
- Testes do verificador Hermes rejeitam alteração em cada grupo de resultados. O verificador temporal existente continua passando.
- Referência externa recebida, casos manuais e resultados gerados localmente devem ser identificados separadamente. Casos novos não serão anunciados como nova paridade Python sem uma referência independente executada.
- Executar testes Swift, suíte raiz, tipos, build e check mobile; preservar os desalinhamentos de patch já conhecidos sem upgrades.
- Revisão do código, build iOS Release com assinatura serial, instalação e abertura autorizadas no iPhone. Operador confirma os três resultados sintéticos e retorno ao fluxo normal. Testes da câmera anteriores só serão repetidos se a mudança os afetar.
- Divergências numéricas são investigadas e relatadas; não relaxar gates nem apresentar paridade parcial como integral.

## Limites e controle

Sem FaceMesh, landmarks, detecção/resize grayscale de boca, features de uma pessoa, encoder, ONNX, templates, decisões de palavra ou inferência real. A origem sintética já contém features e ROIs artificiais; não se conecta automaticamente à captura BGR8.

Igualdade desses cálculos sintéticos não demonstra equivalência de sensores, pré-processamento completo ou R4 real. Direitos e compartilhamento dos artefatos privados continuam pendentes. Sem commit, push, publicação ou alteração de produção; preservar o trabalho local existente.

## Estado da aprovação

Proposta preparada após inspeção das fontes públicas e da fixture entregue. Aguardar aprovação do escopo antes de escrever código de implementação.
