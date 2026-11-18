# IOS-HANDOFF-04 — recebimento dos artefatos privados GLOBAL R4

Data: 30/10/2026. Registro sanitizado de recebimento e integridade, sem dados de templates, embeddings, identificação de participantes ou conteúdo dos manifests privados.

## Resultado

O ZIP `ios-handoff-04-r4-privado.zip` corresponde exatamente ao SHA-256 informado por Andrei:

```text
1c124d8ffcd6bd7f7b6a95b9a1e27e7e9142efa1055ecd1fbe005fa8308a0fe2
```

O conteúdo foi extraído em armazenamento privado fora do repositório, sem sobrescrever arquivos existentes. Diretório criado com permissão 0700 e arquivos com 0600. Os modelos e manifests privados não foram copiados para o Git.

## Verificações executadas no Mac

| Verificação                             | Resultado                                                                                          |
| --------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Ambiente macOS                          | Darwin                                                                                             |
| Hash externo do ZIP                     | Coincide com o esperado                                                                            |
| Inventário                              | 32 arquivos originais; 375.678.464 bytes descompactados                                            |
| Caminhos, duplicatas e links simbólicos | Nenhuma entrada insegura identificada                                                              |
| Manifesto do pacote                     | 31/31 arquivos com tamanho e SHA-256 corretos; somente o próprio manifesto é excluído              |
| Identidades R4 conhecidas               | 14/14 correspondem ao inventário recebido anteriormente                                            |
| Arquivos privados R4 esperados          | Onze presentes, com os hashes esperados                                                            |
| Freeze                                  | Campos de identidade/política conferidos e treze ligações de proveniência consistentes             |
| Código numérico congelado no monorepo   | 8/8 hashes coincidem com a configuração privada recebida                                           |
| Templates DTW                           | 54, nove por classe, Float32 little-endian, 160 features por frame                                 |
| Binário de templates                    | 2.171.520 bytes; hash, offsets, comprimentos, shapes, ordem e finitude conferidos                  |
| Vinculação dos templates à origem       | Hashes de checkpoint, configuração e freeze coincidem com os arquivos recebidos                    |
| Assets MediaPipe                        | Cinco arquivos de referência recebidos; os quatro anteriormente identificados têm os mesmos hashes |

SHA-256 calculado do `manifest.json` recebido:

```text
e014cea3782a0bed5030a699daf503c379dfb2269e0331b04e31a2dca73af786
```

Esse hash identifica o manifesto conferido. Não foi fornecido nesta mensagem um hash esperado separado para ele; a autenticidade do ZIP foi conferida pelo hash externo informado pelo usuário.

As verificações usaram leitura de bytes, JSON, hashes e arrays binários. Os checkpoints PyTorch não foram desserializados e os modelos ONNX não foram carregados. Não foram executados câmera, microfone, inferência, treinamento, Whisper, Piper, Groq ou avaliação held-out. Esta conferência não equivale ao preflight Python completo, que também valida imports, versão do ONNX Runtime e provider.

## Declaração de compartilhamento

O manifesto registra a declaração de João autorizando o compartilhamento privado de modelos, pesos de terceiros e dados derivados com Andrei para o projeto. O próprio registro informa que documentos de terceiros não foram revisados nessa etapa.

Essa declaração foi recebida e registrada como evidência do operador. Não é uma verificação independente das licenças, dos consentimentos ou de autorização para distribuição pública/comercial. O armazenamento e o trabalho permanecem no contexto privado do projeto, conforme o pacote e a solicitação do usuário.

## Efeito sobre a revisão anterior

Este recebimento complementa a [matriz consolidada](2026-10-30-ios-handoff-04.md) e a [solicitação ao João](2026-10-30-ios-handoff-04-solicitacao-joao.md). As afirmações anteriores de que os onze arquivos estavam ausentes descrevem a entrega 03.3; essa ausência foi resolvida para o GLOBAL R4 pelo pacote agora recebido.

| Área                                           | Situação após este recebimento                                                                                                                                                                                                |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Modelos, banco e manifests privados GLOBAL R4  | Recebidos; integridade conferida. Não solicitá-los novamente por ausência.                                                                                                                                                    |
| Exportação dos 54 templates                    | Recebida e validada estruturalmente contra as identidades da origem.                                                                                                                                                          |
| Manifesto do pacote privado                    | Cobertura completa dos arquivos originais, exceto o próprio manifesto. Resolve a cobertura deste pacote, não a do pacote público 03.3.                                                                                        |
| Assets do detector Python                      | Recebidos como referência; completude do grafo, runtime nativo e equivalência iOS continuam por demonstrar.                                                                                                                   |
| Referência canônica                            | Os oito hashes numéricos coincidem com o checkout atual. Manter o código endurecido; não aplicar o overlay histórico. Isso não reproduz automaticamente a base antiga nem os 109 testes do pacote 03.3.                       |
| J1–J5 da revisão de código/contratos           | Não foram entregues arquivos de correção neste ZIP. O README orienta reconciliar esses itens; usar a matriz para distinguir pendências da origem e tarefas do consumidor.                                                     |
| PERSONALIZED                                   | Este pacote não fornece um fluxo pessoal integrado ou perfis reais. Continuam disponíveis as referências sintéticas da entrega anterior; treino e inferência pessoais no iPhone ainda precisam ser implementados e validados. |
| C1/Whisper e saída de voz                      | Checkpoint Whisper/tokenizer, voz e runtimes correspondentes não estão incluídos.                                                                                                                                             |
| Ligação C2 local/C3/voz                        | Não está incluída; permanecem os anexos isolados e os pedidos da revisão.                                                                                                                                                     |
| Entradas reais autorizadas e saídas por etapa  | Não estão incluídas para comparação de paridade no aparelho.                                                                                                                                                                  |
| Operadores/provider, paridade e desempenho iOS | Não testados por este recebimento; dependem da integração e medição no iPhone.                                                                                                                                                |

## Próximo passo

Os artefatos reais do GLOBAL agora estão disponíveis para o trabalho de integração. Preservar esta versão privada e o checkout canônico, fechar a reconciliação dos contratos/referências da revisão e implementar os adaptadores nativos com testes por etapa. Não apresentar a chegada do ZIP como compatibilidade ONNX/MediaPipe comprovada ou como conclusão do escopo GLOBAL + PERSONALIZED + áudio/contexto/voz solicitado por Andrei.

O README recebido limita expressamente o pacote ao GLOBAL R4 e não o apresenta como app iOS executável. A mensagem de encaminhamento não substitui essa verificação do conteúdo.

Nenhum arquivo do aplicativo ou do núcleo foi alterado nesta conferência. Sem instalação de dependências/app, commit, push ou publicação. O recibo detalhado de leitura permanece junto ao armazenamento privado, sem conteúdo de participantes nos logs do chat.
