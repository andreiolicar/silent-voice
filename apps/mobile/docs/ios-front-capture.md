# Ensaio privado de captura frontal

O módulo local `modules/silent-voice-capture` usa Expo Modules e AVFoundation. A rota `/ios-lab` está condicionada à plataforma iOS e a `EXPO_PUBLIC_ENABLE_IOS_LAB=1` na compilação. A flag não é segredo nem concede acesso aos dados autenticados; os guards existentes permanecem. Uma build sem a flag mantém o destino normal do aplicativo.

Este relatório registra o primeiro ensaio de origem em retrato. O modo posterior de conversão horizontal está documentado em [ensaio BGR8](ios-bgr8.md); os resultados dos dois modos são separados.

## Comportamento

- A tela não inicia testes, autorização ou câmera automaticamente.
- O teste sintético gera 121 metadados em Swift, subtraindo uma origem `Int64` alta antes da conversão para JavaScript. O Hermes confere timestamps, gate temporal e mapeamento 0–120 usando o contrato recebido.
- A autorização solicita somente câmera, por toque explícito. A prévia e a aquisição usam a câmera frontal; não há entrada de áudio.
- Cada captura termina após quatro segundos de timestamps recebidos; existe um timeout de segurança de oito segundos e um limite de 256 metadados. Cancelamento, background, remoção da view e interrupções encerram a sessão.
- No modo de origem, o callback acessa o pixel buffer apenas para consultar formato/dimensões e não retém imagens. Não há codificador de vídeo, escrita em arquivo ou envio remoto.
- No modo de origem, os frames reais são identificados como BGRA32/retrato, com dimensões e espelhamento efetivos. Não são convertidos ou renomeados para BGR8. O contrato R4 permanece bloqueado por incompatibilidade de formato nesse modo.
- Os resultados locais mostram contagem, perdas reportadas pelo delegate, duração, FPS e metadados. Logs `SilentVoiceLab` contêm somente resultado sintético ou métricas agregadas, sem pixels, palavras, timestamps absolutos ou identificação de participante.
- O módulo não realiza reconhecimento. Modelos, autorizações e referências privadas continuam necessários para o R4 real.

O botão de retorno usa a sessão e o onboarding atuais: Home para sessão existente, login para onboarding concluído e onboarding para primeiro acesso. Nenhum logout ou nova autenticação é imposto pelo laboratório.

## Verificação automatizada

Na raiz:

```sh
npm test --workspace @silent-voice/mobile
swift test --package-path apps/mobile/modules/silent-voice-capture
```

Os testes Swift rodam no Mac e validam o acumulador, não o hardware do iPhone. Os testes Node verificam a política de entrada, o diagnóstico e o bloqueio do formato de origem. Somente o ensaio na build instalada verifica a ligação Swift/Hermes e a aquisição física.

## Build local de ensaio

Após atualizar o projeto nativo e instalar seus pods, compile pelo Xcode ou CLI. A assinatura deve ser serial, evitando prompts paralelos de chaveiro:

```sh
EXPO_PUBLIC_ENABLE_IOS_LAB=1 xcodebuild \
  -workspace apps/mobile/ios/SilentVoice.xcworkspace \
  -scheme SilentVoice -configuration Release \
  -destination 'id=<IPHONE_UDID>' \
  DEVELOPMENT_TEAM=<TEAM_ID> \
  EXPO_PUBLIC_ENABLE_IOS_LAB=1 \
  COCOAPODS_PARALLEL_CODE_SIGN=false \
  -allowProvisioningUpdates -allowProvisioningDeviceRegistration
```

Não utilizar `expo run:ios` para este ensaio sem verificar seu comportamento de assinatura paralela. Não alterar permissões do chaveiro para contornar solicitações. Os arquivos nativos gerados e credenciais permanecem fora do Git.

## Checklist físico

1. Abrir a tela de ensaio e tocar em Executar teste sintético. Esperado: PASS.
2. Autorizar câmera e capturar quatro segundos. Esperado: prévia frontal durante aquisição, metadados reais, câmera encerrada depois, contrato BLOCKED até normalização BGR8.
3. Iniciar outra captura e cancelar. Esperado: cancelamento controlado, sem resultado reconhecido e câmera encerrada.
4. Iniciar outra captura e colocar o app em background. Esperado: câmera encerrada; ao voltar, permitir novo ensaio.
5. Voltar ao aplicativo. Esperado: destino normal conforme sessão/onboarding.

Não interpretar esses testes como validação de FaceMesh, ROI, tensor, DTW, modelos, reconhecimento GLOBAL ou equivalência de imagens. Registrar separadamente o que o operador confirmou e o que logs/comandos demonstraram.

## Resultado desta execução

Build Release compilada, assinatura validada e instalação/abertura confirmadas por devicectl no iPhone 13, iOS 26.6.2. O operador confirmou o teste sintético Swift → Hermes com 121 frames e resultado PASS.

Na captura frontal, o operador confirmou prévia visível e os seguintes resultados:

| Medida                              | Resultado observado pelo operador |
| ----------------------------------- | --------------------------------- |
| Frames / perdas reportadas          | 121 / 0                           |
| Duração / FPS                       | 4.000 s / 30                      |
| Dimensões / formato de origem       | 480 × 640 / BGRA32                |
| Orientação / espelhamento dos dados | portrait / false                  |
| Normalização BGR8 / inferência      | Indisponíveis                     |

Isso valida esse ensaio de aquisição, não a equivalência de pixels nem a inferência. O operador também confirmou os dois testes de encerramento: cancelar antes de quatro segundos mostrou o cancelamento e apagou o indicador da câmera; sair para background cancelou a captura e, ao retornar, permitiu iniciar outra. Por fim, confirmou o retorno ao fluxo normal pelo botão do laboratório, com a câmera desligada.

Checks de código: quatro testes Swift e 47 testes mobile passaram, além de tipos, lint/formatação e build existentes. A suíte raiz final passou, com três testes PostgreSQL ignorados pela configuração. Uma execução concorrente à compilação nativa falhou no teste de entrada do admin por não encontrar o campo no prazo; a repetição completa passou sem alteração no admin. Expo Doctor/install check mantêm somente os seis desalinhamentos de patch já presentes antes desta integração, sem upgrade de dependências.

Revisão independente identificou e levou à correção do destino de saída do laboratório para preservar a sessão/onboarding. Sem commit, push ou publicação.

O espelhamento do Device Hub exige iOS 27 neste Mac e não foi usado. A evidência visual vem do operador. Houve uma ocorrência inicial de tela preta, sem crash log encontrado para o aplicativo; uma reabertura mostrou o laboratório e permitiu executar o teste sintético. A causa dessa ocorrência não foi confirmada.
