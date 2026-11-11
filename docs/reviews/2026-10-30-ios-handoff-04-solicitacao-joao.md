# Silent Voice — solicitação completa ao João após a revisão iOS

**Data:** 30/10/2026. **Destinatário:** João Xavier / equipe responsável pelo núcleo. **Remetente:** Andrei / equipe do aplicativo iOS.

**Anexo obrigatório:** [IOS-HANDOFF-04 — matriz consolidada do consumidor](2026-10-30-ios-handoff-04.md).

## João, esta é a solicitação consolidada para concluir a entrega

Recebemos e revisamos `ios-handoff-03.3-work.zip`, `local_context.py`, `local_context_v1_contract.md` e `local_context_v1.json`. Precisamos agora fechar todas as dependências de origem para implementar o núcleo completo no aplicativo: **GLOBAL, PERSONALIZED TWO-SHOT, áudio/Whisper C1, C2 local, associação C3 e a ligação com a saída de voz**. O protótipo online deve permanecer identificado separadamente, sem fallback automático para Groq.

Esta solicitação reúne os ajustes J1–J5 e os bloqueios da matriz anexa. Atualiza a solicitação anterior à revisão 03.3, que ainda descrevia somente o C2 remoto. Não é pedido de uma nova auditoria genérica, de outro pacote parcial de preparação ou de reescrever o núcleo.

**Precisamos de uma entrega reproduzível da referência, correções pontuais de contrato, dependências autorizadas e uma resposta objetiva para cada item abaixo.** O que já foi entregue e aprovado deve ser reaproveitado, com referência ao arquivo e ao hash. O que depende de terceiros deve indicar responsável e próxima ação. Não declarar conclusão enquanto uma dependência indispensável estiver ausente.

## 1. O que já está aceito e deve ser preservado

- A especificação da policy temporal v2, suas regras de seleção e limites. No Mac, 312 comparações sintéticas com o TypeScript coincidiram; isso não é validação física universal.
- As formas e operações documentadas de features, ROI, segmentação, seleção dos 29 índices, tensor, DTW, fusão e modelos.
- A distinção entre rejeição com score, rejeição pessoal sem evidência, cancelamento, erro técnico e artefato indisponível.
- O formato portátil dos 54 templates DTW, com offsets, comprimentos, classes e hashes.
- Os 23 arrays do treinamento pessoal sintético, os parâmetros registrados e o perfil sintético com 12 exemplos e head.
- A lógica isolada do C2 local, seus 30 exemplos e os estados RESOLVED, ABSTAIN, INVALID e EXPIRED. Ela é um baseline determinístico de cobertura limitada, não um LLM.
- O princípio ADVISORY_ONLY do C3 anterior: contexto não modifica palavra, score, threshold ou decisão R4.

Não regenerar esses materiais apenas para repetir uma entrega. Reproduzir ou atualizar somente o que mudou ou o que for necessário para corrigir uma lacuna identificada. Manter separadas evidências históricas, sintéticas, operacionais e iOS.

## 2. J1 — referência completa e compatível com o monorepo

- [ ] Identificar repositório, branch e SHA completo da base e listar explicitamente todos os arquivos locais que compõem a referência entregue.
- [ ] Resolver a disponibilidade da base `eb2c348d4ae917b266f41cda8841ffc234840610`: ela não foi encontrada no checkout nem pela API do repositório canônico durante a revisão. Fornecer um archive de fontes verificável, a origem acessível correta ou um patch compatível com a versão canônica.
- [ ] Reconciliar as diferenças em `pyproject.toml`, `live_visual_tester.py`, `global_live_visual_tester.py` e `rejection_4_final_heldout.py`. O checkout revisado foi `c70d517f56ba00ddb0a7052aa483c35b3a28b5d1`; não tratar o overlay antigo como atualização integral da `main`.
- [ ] Preservar as correções já integradas: separação entre raiz pública e raiz privada, verificação da implementação instalada, resolução segura de caminhos e limpeza de clipes limitada aos arquivos efetivamente pertencentes à tentativa. A entrega atual remove partes dessas proteções.
- [ ] Preservar as oito implementações numéricas congeladas e seus hashes aplicáveis. Ajustar empacotamento e suporte sem alterar os algoritmos para acomodar a integração.
- [ ] Entregar o grafo necessário de fontes, scripts, recursos públicos e dependências para reconstruir e importar a referência, sem depender de arquivos soltos no computador do João.
- [ ] Identificar os entry points oficiais de GLOBAL, PERSONALIZED, enrollment/treino, C1, C2 local, C3, saída de voz e protótipo online.
- [ ] Manter explícito que GLOBAL usa `prepare_query` e PERSONALIZED usa `prepare_decoded_query`, com comportamentos distintos para landmarks ausentes. Não substituir silenciosamente o GLOBAL pelo HardenedRuntime.
- [ ] Documentar que vídeo/sidecar/hash são a entrada do runner Python. A futura entrada nativa em memória será implementada no iOS; o aplicativo não deverá gravar MP4 apenas para satisfazer esse envelope.

**Aceite:** uma terceira pessoa consegue reconstruir a referência a partir das fontes identificadas, verificar seus arquivos e executar os testes aplicáveis sem acessar a pasta de trabalho original ou desfazer as correções do monorepo.

## 3. J2 — uma entrega com integridade completa

- [ ] Consolidar código, contratos, exemplos, schemas/validadores, runners, exportadores, geradores, fixtures, perfil sintético e os três anexos do C2 local na entrega de revisão.
- [ ] Incluir um manifesto SHA-256 cobrindo todos os arquivos efetivamente distribuídos, exceto o próprio manifesto, cuja exclusão deve ser declarada. Registrar tamanho e caminho relativo; não omitir exportadores ou arrays pessoais sintéticos.
- [ ] Informar versão da entrega, base de código e hash externo do ZIP pelo canal combinado. O ZIP 03.3 recebido foi identificado no Mac por `032ab66b194e91f33067c7e08baced35cbb9de4eb99caa0db80ea94e5abb9d60`.
- [ ] Manter documentos antigos identificados como históricos e indicar qual documento prevalece. Não atribuir aos 109 testes da origem uma execução que não ocorreu no Mac.
- [ ] Separar o pacote de revisão sem dados pessoais, o pacote de artefatos privados autorizados e o conjunto privado de entradas/resultados de comparação.

**Aceite:** todos os arquivos consumidos têm identidade verificável, não há dependência de caminhos Windows inacessíveis e os materiais privados não são incluídos no pacote de revisão.

## 4. J3 — corrigir apenas a borda de validação C1/C2/C3

Corrigir `reference_contracts.py` e seus testes, preservando os resultados legítimos da referência:

- [ ] C1: validar tipos e coerência dos campos por status. O exemplo NO_SPEECH com `text` não vazio atualmente é aceito; não deve ser apresentado ao consumidor como transcrição válida de silêncio.
- [ ] C2 antigo: validar os tipos de todos os campos serializados, não somente status e vocabulário. Atualmente `topic=123`, `provider=[]` e `context_model_id={}` são aceitos apesar dos tipos documentados.
- [ ] C2 antigo: explicitar campos temporais opcionais, tipos, domínio e ranges. Timestamps negativos e invertidos passaram no aceitador. Distinguir uma estrutura inválida do estado temporal UNKNOWN legítimo previsto no C3.
- [ ] C3 PASS: conferir threshold congelado e coerência `decision = ACCEPT` se e somente se `score >= threshold`, além de preservar a palavra emitida. Hoje C3 aceita `score=0.1`, threshold `0.5666271450980487`, decisão ACCEPT e palavra SIM, enquanto o validador GLOBAL rejeita esse mesmo visual.
- [ ] Manter os exemplos válidos já publicados, os casos de falha/ausência de evidência e UNKNOWN por origem temporal não comprovada ou tempos ausentes.
- [ ] Acrescentar regressões para os contraexemplos da matriz e registrar o comando/resultado dos testes realmente executados sobre os arquivos corrigidos.

**Aceite:** entradas legítimas permanecem válidas; campos com tipos incompatíveis e decisões contraditórias são rejeitados. Não modificar cálculo, pesos, thresholds ou dataclasses congelados para resolver uma lacuna de schema do adaptador.

## 5. J4 — entregar a ligação completa do C2 local

Os anexos definem o interpretador isolado; falta o código necessário para demonstrar sua ligação ao fluxo. Entregar os adaptadores/orquestrador citados na documentação e suas dependências mínimas, sem exigir as janelas Windows no consumidor.

- [ ] Mostrar a sequência completa: captura/transcrição C1 → pergunta válida da sessão → evento visual R4 validado → interpretação local → autorização de saída de voz.
- [ ] Explicar como GLOBAL e PERSONALIZED entram nessa sequência, mantendo o mesmo evento visual aceito e a identidade correta do perfil.
- [ ] Documentar a correspondência de `session_id`, `question_id` e `visual_event_id`, a geração que os mantém e o momento de invalidá-los.
- [ ] Identificar a origem de cada timestamp. C2 local exige relógio monotônico comum; os timestamps visuais relativos a cada tentativa não podem ser comparados diretamente com o relógio de outra origem.
- [ ] Entregar exemplos sintéticos de conclusão normal, REJECT visual, evidência insuficiente, pergunta nova, evento duplicado/antigo, sessão encerrada, cancelamento, resultado tardio, revogação e mudança de perfil.
- [ ] Demonstrar a regra de não produzir voz nem chamar outro provedor em ABSTAIN, INVALID ou EXPIRED; revalidar identidade e validade antes de reproduzir uma resposta assíncrona.
- [ ] Explicitar a convivência com o C3 anterior. `ContextResponse` local é uma frase posterior ao ACCEPT; `ContextResult` antigo é assunto/palavras relevantes com tempos. Não fazer cast entre eles nem apresentar os dois como um único envelope intercambiável.
- [ ] Manter o resultado visual original separado da frase contextual. A interpretação local não pode converter REJECT em ACCEPT nem alterar score/threshold/palavra R4.
- [ ] Apresentar a regra usada para prazo de validade e sua justificativa. Os 300 segundos do generator local e os 120 segundos históricos do C3 não são automaticamente políticas finais do produto.
- [ ] Confirmar modo local como caminho sem rede, sem instanciação do adaptador Groq e sem fallback. Entregar teste sintético que comprove a seleção do adaptador, além da lógica isolada de regras.
- [ ] Identificar a função de `OfflineNetworkGuard` e seus limites. Não tratá-lo como firewall iOS ou garantia sobre bibliotecas nativas/subprocessos.

### Saída de voz usada pelo fluxo

- [ ] Identificar o componente efetivamente usado: adaptador, Piper/engine, versão, voz/idioma, formato de entrada/saída, parâmetros, dependências e arquivos locais necessários.
- [ ] Se houver modelos/vozes externos destinados à entrega, fornecer origem, licenças/avisos, hashes e situação de compartilhamento. Binários Windows não substituem um runtime iOS.
- [ ] Especificar início/fim/erro/cancelamento da fala, fila ou descarte de falas concorrentes e tratamento de resultado tardio.
- [ ] Explicar como a captura de áudio é suspensa ou como a própria fala é excluída do contexto, evitando realimentação; identificar o que a referência ainda não implementa.
- [ ] Indicar quais comportamentos da voz precisam ser preservados no port. A seleção do runtime/voz no iPhone será feita pela equipe iOS; este pedido não encomenda um motor novo nem presume paridade acústica entre engines diferentes.

### Protótipo online, separado

- [ ] Identificar os arquivos e contratos do caminho Groq existente, sua versão/modelo configurado, prompt, formato de resposta, parâmetros, timeouts, consentimento e descarte após revogação.
- [ ] Distinguir o C2 do tester do worker/unified experimental, inclusive se usam modelos diferentes. Fornecer respostas simuladas e respectivos resultados esperados, sem executar novas chamadas externas nesta correção.
- [ ] Documentar exatamente quais dados são enviados e sob qual ação explícita. Não enviar chaves, cookies ou tokens no handoff e não embutir credencial de serviço no aplicativo.

**Aceite:** o ciclo local pode ser exercitado integralmente com entradas e saída de voz simuladas, sem câmera, microfone, rede, pesos privados ou fala real; seus estados e a separação do caminho online ficam inequívocos.

## 6. J5 — referência espacial sintética reproduzível

A fixture atual prova não interferência naquele caso, mas suas ROIs uniformes não distinguem erros espaciais. Preservar esse teste e acrescentar o necessário:

- [ ] Frame(s) BGR uint8 com canais e variação espacial assimétricos, disponibilizando os mesmos bytes efetivamente usados pela referência Python.
- [ ] Landmarks ordenados, máscara de detecção, timestamps e configuração de entrada; detector pode continuar sintético nesse ensaio.
- [ ] Resultados de geometria/transformação, ROI grayscale 96 × 96, features 160D, segmentação, 29 índices e tensor normalizado `[1,1,29,88,88]`.
- [ ] Ao menos um caso com rotação e acesso à borda reflect101; incluir os casos de ausências necessários para distinguir os caminhos GLOBAL/PERSONALIZED já existentes.
- [ ] Shapes, dtypes, ordem de eixos, endianness, hashes e gerador/comando reprodutível de cada array.
- [ ] Se usar MP4 na origem, fornecer os pixels decodificados que chegaram ao pré-processamento. Reencodar o mesmo padrão em outra plataforma não garante a mesma entrada.
- [ ] Resultados esperados produzidos pela referência Python, com teste de que a observação não alterou o comportamento. Não usar a futura implementação Swift para gerar seu próprio esperado.

**Aceite:** conseguimos comparar exatamente a mesma entrada nas duas plataformas e localizar a primeira divergência de canais, transformação, bordas, features, índices ou tensor. Esse material não comprova equivalência do detector facial real.

## 7. Artefatos R4: entregar após as liberações aplicáveis

Precisamos dos onze arquivos privados abaixo para fechar a integração real e a proveniência. Esta tabela reproduz o inventário recebido; não significa que os bytes privados foram verificados no Mac ou que estão liberados. Preservar os caminhos relativos e os bytes congelados; se algum inventário mudar, identificar e justificar a mudança antes de usá-lo.

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

- [ ] Disponibilizar os arquivos autorizados sob raiz privada explícita, com tamanho, SHA-256, versão e árvore de `--artifact-root`. Reutilizar os hashes integrais de `SOURCE_MANIFEST.txt`; incluir esse inventário na entrega final.
- [ ] Manter os três documentos públicos `reference_freeze`, `edge_manifest` e `edge_freeze` nas fontes verificadas. Não misturar raiz pública e privada ou remover a verificação de integridade para passar o preflight.
- [ ] Entregar a exportação autorizada dos **54 templates**, nove por classe, no formato `SV_DTW_TEMPLATES_LE_F32_V1` já revisado: `templates.bin`, manifesto, ordem, shapes `(T,160)`, offsets/comprimentos e hashes dos bytes.
- [ ] Preservar a ligação entre exportação, checkpoint, configuração e freeze de origem; fornecer evidência do round-trip já realizado ou atualizada caso os arquivos mudem. Não repetir a conversão sem necessidade.
- [ ] Distinguir os templates DTW do banco R4 e dos dados embutidos no scorer. Informar quais arquivos são necessários ao cálculo e quais são necessários à verificação de proveniência.
- [ ] Incluir o contrato efetivo dos três ONNX: nomes e ordem de inputs/outputs, shapes, dtypes, IR/opsets, operadores, metadados e configurações relevantes de sessão. Referência: encoder `[1,1,29,88,88] → [1,1664]`; head `[1,1670] → [1,6]`; scorer embedding e índice int64 → score.
- [ ] Registrar runtime/provider de referência e o comando de preflight sem câmera/inferência. Disponibilidade e execução do binário iOS serão verificadas no Mac.

Preservar a ordem `SIM, NÃO, AJUDA, ÁGUA, BANHEIRO, PARAR`, `k=3`, operador `>=` e threshold `0.5666271450980487`. Não treinar novamente, recalibrar, requantizar, substituir pesos ou reexportar modelos para esconder incompatibilidades.

## 8. Detector, pré-processamento e referências reais autorizadas

- [ ] Identificar os assets/grafos efetivos do FaceMesh legado com attention, versões, tamanhos, hashes, origem, licenças e permissões de fornecimento. Disponibilizá-los somente quando autorizado.
- [ ] Manter a configuração do detector, ordem dos 40 pontos, coordenadas, orientação/espelhamento, conversões de cor, normalização, velocidades, smoothing, interpolações, bordas, faltas e fallback vinculados às fontes entregues. Reutilizar a documentação existente onde ela já basta.
- [ ] Confirmar que Face Landmarker nativo não foi demonstrado equivalente ao FaceMesh legado. A escolha e comparação iOS ficam com a equipe do aplicativo; precisamos da referência de origem para compará-los.
- [ ] Após liberação, fornecer um conjunto de desenvolvimento autorizado com as mesmas entradas e saídas intermediárias: landmarks/máscaras, ROI, features, limites/índices, tensor, embedding, distâncias/evidência/fusão GLOBAL, logits, score, decisão e palavra emitida.
- [ ] Incluir casos que permitam conferir as seis classes, rejeição e falta de evidência nos dois modos; documentar cobertura, sem anunciar generalização ou uma nova avaliação científica.
- [ ] Para observar landmarks/ROIs reais não expostos pela interface, fornecer instrumentação mínima revisada e evidência de preservação do comportamento. A instrumentação sintética atual não autoriza coletar dados de pessoas.
- [ ] Identificar o input por hash e formato; respeitar as autorizações do conjunto. Um nome de arquivo ou bloqueio de palavras como `heldout` não comprova autorização.
- [ ] Propor critérios de comparação por etapa antes da execução real: shapes/dtypes/ordens/índices/classes/decisões exatos e tolerâncias numéricas justificadas para os floats. Não relaxar tolerâncias depois de ver falhas e não alterar o threshold.

**Não usar nem reabrir held-out consumido.** Se não houver entradas reais autorizadas, registrar esse bloqueio; as fixtures sintéticas não o substituem como prova de equivalência facial/operacional.

## 9. PERSONALIZED completo: reaproveitar a referência e fechar as lacunas

- [ ] Incluir na entrega final os arrays e o perfil sintéticos já aprovados, seus geradores e metadados, preservando os hashes.
- [ ] Vincular o recipe `LIGHTWEIGHT_PERSONAL_HEAD__2SHOT` à fonte entregue: 12 exemplos válidos, dois por classe; L2 por embedding; `Linear(1664,6)` com bias; seed 2026; CPU Float32; full batch; 500 épocas; CrossEntropyLoss mean; AdamW com parâmetros/defaults registrados; clipping de norma 1.0; sem early stopping.
- [ ] Preservar os pesos/bias iniciais explícitos e os checkpoints 1/2/500, momentos do otimizador e logits finais. Não afirmar que igualar a seed de Swift e PyTorch iguala a inicialização.
- [ ] Consolidar a especificação de enrollment: gate e critérios de validade, repetição de exemplo inválido, extração, progresso, criação, carregamento, seleção, regravação que invalida o head, incompatibilidade de versão/artefato, corrupção e exclusão.
- [ ] Identificar formatos/versionamento dos exemplos/head/manifesto e as dependências que invalidam um perfil. Preservar o scorer e threshold R4 globais na inferência pessoal.
- [ ] Esclarecer as suposições de titularidade e uso por responsável. O vínculo com a conta do app e o isolamento no logout/troca de conta serão implementados aqui; `local_default` não é prova de identidade.
- [ ] Se houver comparação pessoal real liberada, entregar somente o perfil e entradas autorizados para essa finalidade, em armazenamento privado, separados das fixtures públicas. Não criar um perfil pessoal real apenas para preencher esta solicitação.

**Aceite de referência:** conseguimos reproduzir os dados e etapas do treinamento sintético e verificar os estados do perfil. A criação do perfil no iPhone continua sendo requisito de implementação; entregar apenas um head pronto não substitui essa função.

## 10. Whisper e áudio C1: dependências e comparação

- [ ] Fixar o checkpoint destinado à integração, com variante/idioma, tamanho, hash, origem, versão e condições de uso/compartilhamento. O arquivo `small.pt` atual foi documentado com 483.617.219 bytes e SHA-256 `9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794`; confirmar se é o artefato que será fornecido. Não exigir reconstruir um hash histórico nunca registrado.
- [ ] Fornecer, após liberação, checkpoint e recursos necessários de tokenizer/vocabulário/configuração, com inventário e licenças/avisos. Um lock de pacotes não inclui os pesos.
- [ ] Registrar os parâmetros efetivos da referência, incluindo `language=pt`, `fp16=False`, `task=transcribe` e defaults relevantes de decodificação/detecção de silêncio.
- [ ] Reutilizar as referências existentes de captura mono, taxa real, Float32/16 kHz e `resample_poly`. Explicitar duração, descarte do bip/blocos iniciais, clipping/escala, interrupções, falha e descarte de buffers quando esses detalhes não estiverem suficientemente especificados.
- [ ] Incluir os sinais sintéticos, as saídas de resampling e o gerador já entregues. Informar o comportamento para taxas usadas na referência; a equipe iOS verificará a taxa real do aparelho e sua conversão.
- [ ] Entregar entradas de fala e transcrições/estados de referência somente se houver autorização. Registrar comandos, parâmetros e critérios de comparação, sem declarar transcrição real a partir de impulso/silêncio sintético.
- [ ] Preservar a liberação do microfone e o tratamento de cancelamento/encerramento antes da etapa seguinte. Documentar áudio/texto que permanecem apenas em memória e eventuais exceções de persistência.
- [ ] Incluir instruções de reprodução e dependências já verificadas no ambiente de origem. O lock Windows/CPython 3.12 deve continuar identificado como tal; não pedimos um lock Windows renomeado para Mac nem instalação automática aqui.

## 11. Liberações, acesso e responsáveis

Para cada recurso necessário — encoder e derivados, head, scorer com referências, banco, templates, manifests individualizados, detector, Whisper/tokenizer, voz/TTS e entradas/resultados reais — responder:

| Campo obrigatório        | O que informar                                                                                           |
| ------------------------ | -------------------------------------------------------------------------------------------------------- |
| Recurso/versão           | Nome técnico e identidade do arquivo/conjunto                                                            |
| Titular/responsável      | Quem pode confirmar direitos, finalidade e compartilhamento                                              |
| Situação                 | Liberado para a finalidade especificada, bloqueado ou ainda sem confirmação                              |
| Evidência                | Documento/registro e restrições aplicáveis; detalhes sensíveis seguem em privado                         |
| Finalidade/destinatários | Desenvolvimento, integração e teste privado com Andrei/equipe iOS; distinguir de distribuição do produto |
| Canal/custódia           | Meio privado combinado, responsável por acesso/guarda e retenção/descarte                                |
| Pendência                | Ação concreta, responsável e previsão quando conhecida; não inventar datas                               |

- [ ] Coordenar as confirmações com os titulares e responsáveis pelos dados. A autoria dos componentes próprios não resolve automaticamente direitos de pesos externos ou consentimento dos participantes.
- [ ] Identificar responsáveis efetivos quando ainda não foram informados; não devolver somente “aguardando autorização” sem próxima ação.
- [ ] Transferir apenas o que estiver liberado para os destinatários e a finalidade acordados. Se uma pendência impedir a entrega, mantê-la explicitamente bloqueada.
- [ ] Preservar os originais privados necessários à integridade; versões sanitizadas de documentação são arquivos derivados separados, não substitutos silenciosos.
- [ ] Manter gravações, pesos, templates, embeddings/perfis de pessoas, manifests sensíveis e segredos fora do Git comum e dos pacotes de revisão sem dados pessoais.

## 12. Como devolver a entrega e a resposta

Reutilizar os documentos existentes e acrescentar somente o necessário para fechar os itens. Precisamos de:

1. **Pacote de revisão corrigido:** fontes/reconstrução, contratos e validadores, runners/adaptadores, exportadores, fixtures/geradores, instruções e manifesto completo. Incluir o C2 local e a ligação solicitada.
2. **Pacote privado de artefatos autorizados:** árvore relativa, versões, tamanhos, hashes, inventário e permissões. Não adicionar itens ainda bloqueados.
3. **Referências privadas autorizadas:** entradas e resultados intermediários/finais para comparação, com proveniência, parâmetros e critérios acordados.
4. **Resposta item a item:** checklist deste documento e correspondência com J1–J5/M01–M25 da matriz, sem reabrir o que já foi aprovado.

Para cada item, usar **ENTREGUE**, **BLOQUEADO** ou **NÃO IMPLEMENTADO NA REFERÊNCIA**, apontando arquivo/hash/evidência. Se estiver bloqueado, indicar responsável e próxima ação. Se algo não existe no núcleo, dizer isso explicitamente e descrever o comportamento esperado; não produzir uma saída simulada apresentada como real.

Registrar os comandos e resultados dos testes executados sobre os arquivos que mudaram. Preservar as contagens históricas como históricas; não repetir todos os testes/auditorias do Windows sem necessidade e não somar suítes sobrepostas como se fossem evidências independentes. Não executar câmera, microfone, inferência real, Piper, chamadas externas ou avaliações consumidas como efeito colateral desta correção; qualquer comparação real ocorre somente em etapa própria autorizada.

Arquivos locais não são commits publicados. Esta solicitação não autoriza commit, push, merge, publicação, troca de SDK, alteração de produção ou envio de dados a terceiros. Não precisamos de caminhos `C:\Users\...` como entrega: precisamos dos próprios arquivos acessíveis ao Andrei pelo canal combinado.

## 13. O que fica com a equipe iOS

Não é obrigação do João comprovar no Windows o que exige o iPhone. Ficam conosco:

- Seleção e validação dos runtimes ARM64 de detector, ONNX, treinamento pessoal, ASR e voz; medição de cobertura de operadores, provider, memória e latência.
- Entrada nativa em memória, vínculo frame–timestamp, origem temporal comum, orientação, espelhamento, permissões e aquisição no aparelho.
- Implementação Swift dos cálculos e comparadores usando as referências fornecidas.
- Armazenamento privado, integridade de artefatos/perfis, vínculo conta/perfil, sessão/offline e limpeza no logout/troca de conta.
- Cancelamento, geração/ID de operação, descarte de respostas tardias, background/interrupção e controle de câmera/microfone/voz.
- Integração à experiência normal autenticada, build/assinatura/instalação e testes no iPhone físico. Se o caminho online for mantido, definir a fronteira autenticada de serviço sem chave embutida no app e separada do chatbot comercial.
- Aprovação prévia dos critérios de comparação e das escolhas de produto ainda abertas, incluindo frescor contextual e voz; validação final dos três fluxos.

## 14. Critério de conclusão

**Entrega de origem concluída:** J1–J5 corrigidos; referência reconstruível; todos os componentes necessários acessíveis de forma autorizada; contratos e dependências identificados; referências suficientes para comparar cada etapa; nenhum bloqueio indispensável oculto por um rótulo de progresso.

**Integração concluída:** GLOBAL, criação/uso de perfil PERSONALIZED, C1, C2 local, associação contextual e saída de voz funcionando no aplicativo normal com dependências reais autorizadas; comparação por etapa conforme os critérios acordados; permissões, interrupções, identidade, expiração e cancelamento validados; medições no iPhone e checks/revisão do código concluídos.

`READY FOR IOS CONSUMER REVIEW` não significa `HANDOFF READY`, e nenhum desses estados significa `IOS VALIDADO`. “100% do núcleo” é cobertura funcional do escopo combinado, não promessa de 100% de acurácia ou prova antecipada de equivalência.

João, devolva os materiais e a resposta consolidada acima. Quando algo depender de uma liberação externa, queremos o impedimento e o responsável identificados; quando depender do iPhone, registramos a tarefa do nosso lado. O objetivo deste retorno é permitir uma implementação completa com evidências, sem outro ciclo genérico de preparação.
