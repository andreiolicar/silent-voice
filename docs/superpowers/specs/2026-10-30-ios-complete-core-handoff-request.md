# IOS-HANDOFF-03 — solicitação para integração integral do núcleo

Data: 30/10/2026. Documento preparado para Andrei encaminhar ao João; não foi enviado automaticamente.

## Objetivo confirmado por Andrei

Integrar ao aplicativo iOS o núcleo completo existente: **GLOBAL, PERSONALIZED TWO-SHOT, áudio C1, interpretação contextual C2 e associação observacional C3**. A entrega final deve funcionar na experiência normal autenticada do aplicativo, com ensaio e evidências no iPhone físico. A proposta anterior de um ciclo isolado de cálculos sintéticos não foi aprovada; seus testes passam a ser parte da integração completa.

Completo significa cobertura funcional dos comportamentos existentes e validação da integração. Não significa 100% de acurácia, equivalência numérica já demonstrada ou funcionamento integral offline: o C2 atual consulta Groq. Não inventar um substituto offline nem remover esse componente silenciosamente.

## Mensagem para João

João, vamos concluir a integração integral do núcleo que você criou no aplicativo iOS do Andrei, incluindo GLOBAL, PERSONALIZED e áudio/contexto. Precisamos consolidar as dependências e fechar o handoff em uma única entrega rastreável, em vez de continuar recebendo pacotes de preparação parciais.

No Mac, já compilamos, assinamos, instalamos e abrimos uma build privada no iPhone 13. O operador validou captura frontal de quatro segundos, cancelamento/background, teste temporal Swift → Hermes e empacotamento horizontal BGRA32 → BGR8 640 × 480, com gate técnico PASS. Isso ainda não é execução do R4.

Você não precisa compilar iOS no Windows. A parte nativa, integração ao aplicativo, assinatura, instalação e medição no aparelho ficam conosco. Precisamos de você nas fontes, artefatos, referência Python e esclarecimentos científicos/técnicos abaixo. Não reabra nem repita a avaliação held-out consumida.

### 1. Versão completa e escopo funcional

- Informar repositório, branch e SHA completo do commit que representa o núcleo a integrar. Listar o que está no monorepo e o que ainda é somente local. Não declarar arquivos locais como entregues no Git; fornecer patch/pacote público revisável se ainda não houver commit autorizado.
- Entregar um mapa de entrada/saída e dependências para GLOBAL, PERSONALIZED, C1/C2/C3, com testes e comandos reprodutíveis da versão entregue.
- Identificar os entry points oficiais. Há código R4 GLOBAL que usa `prepare_query` e código PERSONALIZED que usa `landmark_gap_runtime.prepare_decoded_query`; os tratamentos de landmarks ausentes diferem. Confirmar o caminho correto por modo e quais políticas estão aprovadas para esta integração. Não unificar ou substituir comportamentos silenciosamente.
- Informar lacunas ou funções incompletas da própria referência. Separar resultado histórico, teste sintético, teste operacional real e pendência. Não declarar validação iOS que você não executou.

### 2. Liberações e entrega privada

- Para cada modelo, peso derivado, banco, template, manifesto e entrada de comparação, informar responsável pela liberação, finalidade permitida, destinatário, restrições, situação e evidência correspondente. A declaração de uso dos componentes próprios não resolve automaticamente os direitos de componentes externos ou de dados incorporados.
- Confirmar os termos aplicáveis aos pesos SwinLip/LRW e seus derivados, assets MediaPipe, checkpoint Whisper e dados utilizados. Resolver as pendências já registradas no handoff anterior com os responsáveis pertinentes.
- Se algum item não estiver liberado, **não transferi-lo**. Registrar exatamente o item, o impedimento, quem precisa resolvê-lo e a próxima ação. Não trocar por outro peso/dataset para aparentar uma entrega completa.
- Após liberação, combinar com Andrei canal privado, acesso, guarda e retenção. Nenhum artefato privado, gravação, perfil, embedding individualizado ou segredo entra no Git comum, ZIP público ou mensagem pública.
- Entregar o pacote autorizado com versão, árvore relativa de `--artifact-root`, tamanho e SHA-256 de cada arquivo, manifesto do pacote e hash externo do ZIP. Preservar os bytes dos artefatos congelados. Manifests sanitizados de documentação são derivados separados, não substitutos dos originais exigidos pelo preflight.

### 3. Pacote R4 completo e exportação dos templates

O inventário recebido tem três documentos públicos e **onze arquivos privados**. Confirmar a lista e seus hashes, fornecer os itens autorizados e relatar dependências adicionais da versão final:

| Nome                    | Caminho relativo esperado                                                    |
| ----------------------- | ---------------------------------------------------------------------------- |
| encoder                 | `data/processed/models/edge/cycle_06_swinlip_clip_encoder_fp16.onnx`         |
| head                    | `data/processed/models/edge/cycle_06_positive_head_fp32.onnx`                |
| edge_scorer             | `data/processed/models/rejection_4/rejection_4_top3_policy.onnx`             |
| positive_checkpoint     | `data/processed/models/cycle_06_hybrid_positive_classifier.pt`               |
| reference_bank          | `data/processed/models/rejection_4/rejection_4_top3_reference_bank.npz`      |
| positive_config         | `data/processed/evaluation/cycle_06_positive_classifier_final_config.json`   |
| edge_config             | `data/processed/evaluation/cycle_06_edge_preheldout_final_config.json`       |
| edge_centroids          | `data/processed/models/edge/cycle_06_onnx_fp16_rejection_clip_centroids.npz` |
| edge_origin_manifest    | `data/processed/evaluation/cycle_06_preheldout_freeze_manifest.json`         |
| reference_bank_manifest | `docs/cycles/rejection_4_reference_bank_manifest.json`                       |
| final_freeze            | `docs/cycles/rejection_4_final_freeze.json`                                  |

- Entregar um exportador reprodutível dos **54 templates do checkpoint positivo**, nove por classe, para formato de dados documentado legível no iOS sem Python, pickle ou PyTorch. Podemos consumir arrays binários little-endian com offsets/dimensões em JSON; confirmar esquema junto com a entrega. O exportador deve preservar ordem, dtype, valores, shapes, classes e associação de proveniência dos templates, com hashes dos bytes de origem e derivados e verificação de round-trip.
- Não confundir os 54 templates DTW com o banco de referência R4. Informar exatamente quais dados ficam embutidos no scorer ONNX e quais o runtime precisa carregar separadamente. Separar dependências de execução das de verificação de proveniência.
- Fornecer nomes/dtypes/shapes de entradas e saídas, opsets/IR, metadados customizados, operadores e configurações de sessão dos três ONNX efetivos. A inspeção anterior registrou encoder `[1,1,29,88,88] → [1,1664]`, head `[1,1670] → [1,6]` e scorer embedding + índice int64 → score; confirmar contra os bytes entregues.
- Não reexportar/requantizar os três modelos congelados para resolver iOS nesta entrega. Se houver incompatibilidade, relatá-la; uma conversão futura precisará de identidade própria e comparação aprovada.

### 4. Pré-processamento e referência numérica ponta a ponta

- Consolidar a especificação implementada: orientação/espelhamento, BGR/RGB/grayscale, configuração e assets do FaceMesh legado com attention, ordem dos 40 pontos, normalização geométrica, velocidades/features 160D, máscaras e ausências, ROI affine 96 × 96, interpolação/bordas/arredondamento, segmentação, 29 índices, tensor 88 × 88, DTW, evidência recíproca, fusão 1670D, logits, desempates e rejeição.
- Identificar grafo/modelos exatos e licenças do detector. Explicar o que precisa ser preservado no iOS; Face Landmarker e FaceMesh legado não serão tratados como equivalentes só por terem a mesma quantidade de pontos. A seleção e a prova do detector nativo ficam conosco, usando sua referência.
- Entregar um runner de referência que use o runtime normal e permita comparar etapas isoladas. Não chamar o avaliador one-shot nem reutilizar held-out consumido. Documentar versões, comandos, entrada, saída, formato de arrays e logs sanitizados; não exigir leitura de outros diretórios de dados.
- Ampliar as fixtures sintéticas recebidas para cobrir limites temporais/holds/gaps/arredondamento, landmarks/máscaras, geometria/ROI/features, segmentação/índices, tensor, DTW e fusão. Resultados esperados devem ser gerados pela referência, não pelo código iOS sob teste.
- Após as liberações, fornecer um conjunto de desenvolvimento autorizado para comparação dos mesmos bytes de entrada, com saídas intermediárias e resultado final GLOBAL/PERSONALIZED. Cobrir as seis classes, rejeição e falha de evidência; distinguir cobertura de integração de avaliação científica. Se não houver entradas faciais autorizadas, registrar explicitamente que a equivalência do detector e do caminho real continua bloqueada.
- Apresentar critérios numéricos justificados por etapa antes da comparação. As tolerâncias exploratórias do pacote parcial não estão aprovadas automaticamente. Shapes, ordem de classes/índices e decisões finais devem ser exatos; não alterar thresholds para fazer o port passar.
- Preservar classes `SIM, NÃO, AJUDA, ÁGUA, BANHEIRO, PARAR`, R4 `k=3`, operador `>=` e threshold `0.5666271450980487`, salvo mudança formal de versão solicitada e validada separadamente.

### 5. PERSONALIZED completo, incluindo criação do perfil no aparelho

- Entregar o contrato de enrollment de dois exemplos válidos por palavra, total 12, critérios de validade, extração dos embeddings/features, progresso, repetição, invalidação do head ao regravar, criação/carregamento/seleção/exclusão e tratamento de arquivos incompletos ou adulterados.
- Documentar o recipe efetivo `LIGHTWEIGHT_PERSONAL_HEAD__2SHOT`: normalização, seed, inicialização de `Linear(1664,6)`, ordem dos 12 exemplos, loss/redução, AdamW e todos os parâmetros/defaults, 500 épocas, clipping, dtypes e regras determinísticas. A criação do perfil deve continuar local; carregar apenas um head pré-treinado não cobre esse requisito.
- Fornecer fixtures de enrollment sintético com embeddings de entrada, pesos/bias iniciais explícitos, checkpoints de passos do otimizador, pesos/bias finais e logits/decisões esperados. Precisamos separar paridade do treinamento da diferença entre os geradores aleatórios de PyTorch e Swift. Uma adaptação da inicialização/treinamento precisa ser declarada, não apresentada como reprodução exata.
- Documentar formato/versionamento dos exemplos, head, manifesto, hashes e identidade das dependências. Fornecer exportação de referência de um perfil **sintético**, sem usar o perfil de uma pessoa como fixture pública.
- Confirmar que PERSONALIZED reutiliza encoder e scorer/threshold R4 globais e qual pré-processamento de ausências é aplicado. Listar quando um perfil se torna incompatível e deve bloquear a inferência.
- Informar as suposições atuais sobre titular do perfil e uso por responsável. Nós implementaremos o vínculo com a conta do app e o isolamento no logout/troca de conta; `local_default` não será tratado como autenticação.

### 6. Áudio C1, contexto C2 e integração C3 completos

- Identificar o checkpoint Whisper efetivamente usado, tamanho/hash, idioma, versão/licença, tokenizer/vocabulário e demais arquivos necessários. `small.pt` aparece como exemplo de documentação; precisamos da identidade real, não presumir que esse arquivo foi entregue. Confirmar `language=pt`, `fp16=False`, `task=transcribe` e todos os parâmetros/defaults relevantes.
- Documentar captura mono, duração, taxa real, conversão para Float32/16 kHz via `resample_poly`, tratamento do bip inicial e blocos descartados, silêncio, erros, interrupção e descarte. Entregar sinais sintéticos e resultados de resampling; para avaliação de transcrição, usar apenas fala autorizada e identificar a origem.
- Fornecer as saídas e critérios de comparação de Whisper de referência. A escolha do runtime nativo e eventual conversão de formato do Whisper serão validadas no Mac/iPhone; não presumir que um runtime nativo reproduz automaticamente o PyTorch.
- Consolidar o contrato C2 Groq: modelo configurado, prompt, parâmetros, formato JSON, normalização das seis palavras, timeouts, erros, revogação e respostas tardias. No código atual o modelo configurado é `openai/gpt-oss-20b`; registrar a versão usada e como conferir sua disponibilidade. Fornecer testes com respostas simuladas e casos autorizados; não enviar chaves de API.
- Confirmar a fronteira de dados: somente transcrição segue ao C2 quando o operador ativa a autorização de sessão; áudio bruto, vídeo, templates e perfis não são enviados. O cliente móvel não receberá uma chave Groq embutida: implementaremos um adaptador autenticado no backend, separado do chatbot comercial, se preservarmos esse provedor.
- Explicitar que C2 exige rede no desenho atual. Falta de rede/credencial/provedor deve afetar o contexto, sem simular uma resposta e sem interromper automaticamente o reconhecimento visual local.
- Entregar fixtures C3 `ADVISORY_ONLY`: relógio monotônico comum, ausência de prazo contextual, contexto atual/expirado, resposta posterior à decisão, estados indisponíveis e invariância de palavra/score/threshold/ACCEPT/REJECT em GLOBAL e PERSONALIZED.
- Não definir 120 segundos como política final: a documentação o identifica como valor experimental. Apresentar recomendação de prazo/frescor com justificativa para a equipe decidir antes da validação operacional.
- Confirmar o comportamento previsto durante TTS do aplicativo para evitar realimentação na captura contextual. Se a referência não o implementa, registrar a lacuna e sugerir a regra, sem declarar cobertura existente. Esta solicitação não inclui criar um motor novo de TTS.
- O lock Windows atual não cobre todo o extra áudio. Entregar dependências e instruções reprodutíveis suficientes para exercitar C1/C2/C3 no ambiente de referência; separar o que realmente foi executado do que é só instrução.

### 7. Contratos e falhas para o aplicativo

Entregar proposta versionada, derivada do comportamento real, para entrada/saída e estados de GLOBAL, PERSONALIZED, enrollment/treino, áudio/contexto e indisponibilidade. Especificar unidades, campos opcionais e exemplos sintéticos. Separar cancelamento, erro técnico, artefato indisponível/incompatível, ausência de evidência e rejeição normal. Em REJECT não emitir a hipótese interna como palavra reconhecida. Scores não viram porcentagens de confiança por conta própria.

Não adicionar HTTP/USB/BLE/Wi-Fi ao núcleo como parte do handoff, não criar um segundo login e não pedir tokens/cookies do app para o Python. A equipe do aplicativo implementará os adaptadores e as regras de sessão existentes.

### 8. Resposta final e critério de fechamento do handoff

Entregar `README_INTEGRATION`, inventário/hashes, exportadores e schemas, runner/fixtures/resultados, matriz de permissões e tabela de pendências com responsável e próxima ação. Para cada requisito acima, marcar **ENTREGUE, BLOQUEADO ou NÃO IMPLEMENTADO NA REFERÊNCIA**, apontando a evidência. Não responder apenas que os testes passaram.

O handoff só está completo quando os componentes necessários estão acessíveis de forma autorizada, suas identidades e contratos são verificáveis e podemos reproduzir a referência nos três fluxos. Se qualquer liberação ou dependência ainda estiver pendente, informar exatamente o que falta. `HANDOFF READY` não significa `IOS VALIDADO`: a conclusão da integração depende da compilação, paridade e testes reais no iPhone que faremos depois.

## Responsabilidades e definição de integração concluída

**João/equipe de origem:** fechar versão, especificar comportamento, fornecer runner, referências e exportações, coordenar com os responsáveis as liberações e disponibilizar os artefatos autorizados. João não deve atestar direitos de terceiros por simples autoria dos componentes próprios.

**Equipe do aplicativo no Mac:** selecionar e validar detector/runtime ARM64, implementar todos os adaptadores, armazenamento privado e integridade, port numérico, treinamento pessoal local, Whisper, áudio nativo, backend contextual autenticado, UX e vínculo conta/perfil. Reutilizar o trabalho de captura existente. Não transferir para João a obrigação de provar execução no iPhone que ele não possui.

**Concluído no iPhone:** execução dos três fluxos com dependências reais autorizadas; paridade por etapa e decisões conforme critérios previamente definidos; captura/treino/transcrição fora da thread de UI; medição de tempo/memória/FPS no aparelho; interrupções e permissões verificadas; troca de conta/perfil e logout sem exposição de dados; revogação contextual efetiva; falha de contexto sem alterar R4; retorno ao fluxo normal; checks de código e revisão concluídos. A UI normal deve consumir o runtime real, sem resultados simulados apresentados como reconhecimento.

O desenho atual oferece reconhecimento visual local e contexto remoto opcional. Tornar também o contexto inteiramente offline é outro requisito e exigiria escolher/validar um modelo local; não está implementado na referência e não foi inferido desta solicitação.

## Evidências consultadas nesta preparação

- Handoffs recebidos `app_integration_handoff.md`, `ios_handoff_01c_private_report.md` e README/gerador do ZIP IOS-HANDOFF-02.4.
- SHA-256 do ZIP novamente conferido: `addd0dcf998c3ad8cccb78ec39234e3d043c83d87b5fb5cd2a3c71a5b4e4fb5f`.
- Fontes públicas locais: `live_visual_tester.py`, `rejection_4_final_heldout.py`, `cycle_06_final_heldout.py`, `landmark_gap_runtime.py`, `detector.py`, `temporal_features.py`, `hybrid_features.py`, `positive_classifier_final.py`, `personal_live_visual_tester.py`, `visual_personalization_candidates.py`, `contextual_audio.py`, `context_interpreter.py`, `live_context_session.py`, `context_advisory.py`.
- Documentação `ai/docs/global_live_visual_tester.md`, `python_reproducibility.md` e `c44_live_tester_reproducibility.md`; resultados anteriores do iPhone em `apps/mobile/docs/ios-front-capture.md` e `ios-bgr8.md`.
- Esta preparação não executou modelos, treino pessoal, captura/transcrição, Groq ou avaliações científicas. Não acessou artefatos privados nem alterou o aplicativo.
