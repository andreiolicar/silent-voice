# C4.1 — Global Live Visual Tester experimental

Esta interface local usa o runtime visual **R4** já congelado. O modo GLOBAL
não exige enrollment ou perfil individual. O rótulo **EXPERIMENTAL** indica
que o desempenho em novos usuários não foi estabelecido cientificamente.

## Iniciar

Na raiz do repositório, com a virtualenv existente:

```powershell
.\.venv\Scripts\python.exe -m scripts.demo.global_live_visual_tester --visual-preview
```

Esse comando exibe somente a composição visual sintética. Não abre câmera,
microfone ou modelos, não cria clipe e não consulta serviços externos. A
prévia deixa a captura desabilitada.

Para uma futura demonstração supervisionada, com acesso autorizado à câmera:

```powershell
.\.venv\Scripts\python.exe -m scripts.demo.global_live_visual_tester --camera-index 1
```

O índice é mostrado no card da câmera. Se a fonte estiver indisponível, a
janela mostra erro técnico; outro índice pode ser informado no comando de
inicialização. A janela não alterna automaticamente de dispositivo.

## Controles e estados

`ESPAÇO` ou o botão **Capturar / repetir** inicia uma única captura manual.
`D` ou **Depuração** mostra score e hipótese interna. `ESC`, `Q` ou **Sair**
encerra a sessão e libera a câmera. Os clipes de trabalho ficam somente em
`data/processed/live_tester/tmp/` e são removidos depois do processamento.
`--keep-clips` retém explicitamente clipes na área diagnóstica, fora dos
datasets científicos.

A janela distingue AGUARDANDO, CAPTURANDO, PROCESSANDO, ACCEPT, REJECT e
ERRO TÉCNICO. Uma captura inválida pela política temporal v2 não chega à
inferência: mostra falha técnica e permite repetição manual. Uma rejeição
não exibe a hipótese interna como palavra reconhecida. O score exibido é
do modelo R4 e não uma probabilidade calibrada. A mensagem técnica completa
fica acessível por clique em uma janela de detalhes e no terminal quando não
cabe no card.

Os dados de câmera são apresentados em 4:3, sem deformação. A janela usa
OpenCV e Pillow já disponíveis no ambiente do repositório; a captura e a
inferência rodam fora do loop gráfico. A interface preserva o pipeline
existente: captura e normalização temporal, preprocessing, SwinLip,
Positive Head e rejeição R4. O fluxo C1/C2/C3 só é acionado quando o áudio
contextual é ativado na sessão.

O card **Contexto com IA** começa com áudio e IA desativados. Nenhum acesso ao
microfone ou envio externo ocorre ao iniciar a janela. A prévia sintética
mostra os controles, mas não pode ativá-los.

## C4.P — Meu Perfil TWO-SHOT

O painel **Meu Perfil** permite gravar ou regravar, por ação explícita, dois
exemplos de cada palavra na ordem SIM, NÃO, AJUDA, ÁGUA, BANHEIRO e PARAR. O
progresso só aumenta após o gate temporal v2 e a extração visual válidos. Um
exemplo reprovado pode ser repetido manualmente e não entra nos 12 aceitos.

Com 12/12 exemplos, **Criar perfil** executa o recipe histórico
`LIGHTWEIGHT_PERSONAL_HEAD__2SHOT`: SwinLip congelado, embedding de 1664
dimensões e `Linear(1664,6)` treinado por 500 épocas fixas em CPU. A cabeça
pessoal escolhe a classe; o scorer e o threshold globais R4 permanecem os
mesmos. O modo inicial continua GLOBAL. O seletor PERSONALIZED só fica ativo
com perfil local compatível; a troca não reinicia a câmera.

Os exemplos derivados, o head e o manifesto ficam apenas em
`data/processed/live_tester/profiles/<profile_id>/`, área ignorada pelo Git e
separada dos datasets científicos. O MP4 de cada gravação é temporário e
removido após a extração. O carregamento verifica hashes, ordem das classes,
recipe e proveniência R4. **Excluir perfil** remove somente os arquivos
conhecidos desse diretório local; arquivos inesperados bloqueiam a exclusão.
Regravar qualquer exemplo invalida o head anterior até uma nova criação.

Para selecionar explicitamente outro perfil local antes de abrir a câmera,
use `--profile-id synthetic_profile` no comando do tester. O ID ativo
aparece na janela e no painel Meu Perfil; capturas PERSONALIZED registram o
ID e a versão do perfil no log. Sem essa flag, o perfil legado continua
`local_default`. IDs aceitam somente letras ASCII, números, `_` e `-`, com
até 48 caracteres. Cada ID usa um diretório isolado; o comando não copia
exemplos de outro perfil.

`--visual-preview` exibe também o painel sintético, com gravação e criação
desabilitadas. Esta etapa não comprova ganho de acurácia para um usuário real;
os 12 vídeos de enrollment não constituem avaliação independente. A seção
C4.P descreve apenas a personalização; C4.3 continua fora do escopo atual.

## C4.2 — contexto observacional

Para uma execução operacional futura, informe o checkpoint Whisper local e,
se desejar classificar a validade temporal, um prazo explícito para esta
execução. O valor de 120 segundos usado no smoke C3.1 foi experimental e não
é uma política automática do produto.

```powershell
.\.venv\Scripts\python.exe -m scripts.demo.global_live_visual_tester --camera-index 1 --whisper-model-path "CAMINHO_LOCAL_DO_SMALL.PT" --audio-device 1 --audio-sample-rate 44100 --context-max-age-seconds 120
```

O comando acima está documentado para o teste supervisionado posterior; não
foi executado no C4.2. Os parâmetros de dispositivo e taxa podem ser omitidos
para usar a entrada padrão e sua taxa real. Sem `--context-max-age-seconds`, o
C3 informa `TEMPORAL_UNKNOWN` para contexto disponível, sem presumir frescor.

O operador ativa **Áudio** na janela antes da primeira tentativa contextual.
Cada clique em **Capturar** faz uma única captura de áudio de até cinco
segundos, depois uma captura visual. Após abrir o microfone, um bip de 880 Hz
por 150 ms indica quando falar; os blocos recebidos até o fim do bip são
descartados. O C1 libera o dispositivo antes de transcrever localmente em
português. Áudio e transcrição não são salvos pelo fluxo contextual.

**Ativar IA** autoriza, apenas nesta sessão, o envio automático de cada texto
transcrito ao cliente Groq C2 existente. O botão não envia nada por si só.
Desativar impede novos pedidos; uma resposta tardia após revogação é ignorada.
Fechar a janela extingue a autorização. Somente o texto transcrito é enviado:
vídeo, frames, áudio bruto, perfis e datasets não são enviados.

O painel apresenta estados de áudio, Whisper e Groq, assunto, palavras
contextualmente relevantes, relação C3 e latências disponíveis. O C3 usa o
mesmo relógio monotônico de C1/C2 e da decisão visual; sem prazo configurado
ou timestamps suficientes, não afirma que o contexto está atual. A política
`ADVISORY_ONLY` preserva ACCEPT, REJECT, score e threshold tanto em GLOBAL
quanto em PERSONALIZED. `NOT_SUGGESTED` significa apenas que a palavra visual
não apareceu entre as sugestões contextuais. O resultado não altera a palavra
reconhecida.

Esta integração foi validada somente com dispositivos, texto e resultados
visuais sintéticos. O teste operacional real pertence ao C4.3.

## C4-FPS-MEASURE — diagnóstico supervisionado de cadência

O diagnóstico é opcional e não muda a policy temporal v2 nem os modelos. Ele
registra apenas tempos e métricas em JSON, sem frames ou áudio. Inicie somente
com o operador presente e a câmera disponível:

```powershell
.\.venv\Scripts\python.exe -m scripts.demo.global_live_visual_tester --camera-index 1 --fps-diagnostic
```

Com ÁUDIO e IA desligados, pressione **ESPAÇO** para uma captura A normal.
Depois que ela terminar, pressione **F** uma vez; o terminal confirmará
`NO_REDRAW`. Pressione **ESPAÇO** para a captura B, que mantém a aquisição e o
gate, mas congela o desenho da janela durante os quatro segundos. **F** alterna
de volta para `NORMAL` apenas quando não há captura em andamento. Use **ESC**
para encerrar. Não execute capturas simultâneas ou uma repetição automática.

Cada tentativa gera um arquivo distinto
`data/processed/live_tester/logs/fps_diagnostic_<attempt_id>.json`. O terminal
mostra o caminho. O JSON contém os instantes monotônicos de início e fim de
cada `camera.read()`, o timestamp efetivamente passado à policy, os tempos de
cópia e da callback de prévia, os intervalos de desenho da janela, contagem,
duração, FPS e resultado do gate, inclusive quando ele bloqueia. `read_status`
distingue leitura válida, falha e formato inválido. `ui_update_start_ns` e
`ui_update_end_ns` medem o envio do frame ao painel; `ui_updates` mede a
renderização e o `imshow` na thread gráfica. O diagnóstico não retém MP4; uma
captura válida ainda segue o fluxo normal de MP4 temporário e inferência R4.

Para comparar A e B, use `source_fps_effective` e `technical_failures` do
`gate`, além dos intervalos entre `policy_timestamp_ns` sucessivos. Se B
melhorar mantendo os tempos de `camera.read()` próximos aos de A, a
renderização ou sua competição por recursos merece investigação. Se ambas
apresentarem leituras lentas, examine a entrega da Iriun e a configuração
efetiva do backend. Compare também o tempo das cópias e de `ui_updates`;
nenhuma diferença isolada comprova causalidade. Um PASS isolado não valida a
câmera nem autoriza alteração dos limites científicos.
