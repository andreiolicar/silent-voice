# Ensaio privado de captura frontal no iPhone

## Objetivo

Adicionar uma área privada de ensaio à build local para validar a ligação Expo/Swift, executar um caso temporal sintético no Hermes e adquirir quatro segundos de metadados da câmera frontal. A entrega deve distinguir aquisição de câmera, normalização de pixels e reconhecimento R4.

## Decisão arquitetural proposta

Usar um módulo Expo local em `apps/mobile/modules/silent-voice-capture`, com Swift e AVFoundation. A UI depende de um adaptador TypeScript, sem acesso direto às APIs AVFoundation. O módulo não implementa o gateway USB nem substitui `SilentVoiceDevice`.

Esta é minha recomendação técnica. O `expo-camera` documenta prévia, fotos e gravação em cache; um adaptador AVFoundation dá acesso aos callbacks de frames, seus presentation timestamps e descartes. Uma biblioteca externa de processamento de frames adicionaria dependências e outro runtime antes de termos o pré-processamento R4 definido. Aguardar os pesos atrasaria testes de aquisição que podem ser realizados sem eles.

## Limites

- Preservar Expo 57, versões, autenticação, telas Live e fluxo USB/Raspberry.
- Não implementar ONNX, MediaPipe, inferência, palavras reconhecidas ou reprodução de voz.
- Nenhuma foto, vídeo ou buffer de imagem persistido, transmitido ou incluído em logs. Não adicionar acesso ao microfone.
- Buffers de câmera são descartados ao terminar cada callback. Retornar somente uma coleção limitada de metadados e contagem de perdas.
- O formato capturado será informado fielmente (por exemplo, BGRA32 e dimensões de saída em retrato). Não rotular esses buffers como BGR8 640 × 480. A conversão e a comparação de pixels são outro incremento.
- O contrato recebido permanece congelado. Uma captura que não satisfaz seu formato deve continuar bloqueada.
- Sem commit, push ou publicação.

## Acesso e interface

Criar a rota `/ios-lab`, incluída somente quando a build iOS recebe `EXPO_PUBLIC_ENABLE_IOS_LAB=1`. O sinalizador é configuração pública de build, não segredo. Essa rota permite somente ensaios locais e não expõe sessão, histórico ou informações de conta. As demais rotas protegidas continuam com seus guards.

Na build de ensaio, a abertura inicial pode direcionar para essa rota. A build normal, sem a flag, mantém o destino atual. A tela usa componentes e tokens existentes, com os controles:

1. Executar teste sintético: sem câmera nem permissão, solicitar 121 timestamps relativos calculados em Swift e validar no Hermes com `analyzeCapture`. Conferir amostras literais de timestamps e o mapeamento 0–120.
2. Autorizar câmera: solicitar somente acesso à câmera após toque explícito; negar ou restringir mantém a captura bloqueada.
3. Capturar quatro segundos: abrir a câmera frontal, mostrar prévia e retornar metadados reais. Exibir contagem, duração, FPS observado, perdas, formato, dimensões, espelhamento e bloqueio do contrato quando aplicável.
4. Cancelar: interromper a sessão e descartar a aquisição em andamento. Sair da rota, perder foco ou colocar o app em background também deve interromper a câmera.

Nenhum teste, pedido de permissão ou captura inicia automaticamente ao abrir a tela. A interface mostra que o reconhecimento está indisponível e que se trata de uma build de ensaio.

## Contrato do adaptador

- `getPermission(): Promise<'undetermined' | 'granted' | 'denied' | 'restricted'>`.
- `requestPermission(): Promise<Permission>`.
- `syntheticFrames(): Promise<CapturedFrame[]>`: dados aritméticos, 121 frames, 30 FPS, origem absoluta alta subtraída em precisão nativa; nenhum dispositivo aberto.
- View nativa de prévia com `capture(): Promise<NativeCaptureReport>` e `cancel(): Promise<void>`.
- `NativeCaptureReport`: status `complete | cancelled | camera-error`, frames com metadados efetivos e timestamps relativos, `readFailures` inteiro não negativo e código controlado de erro opcional.
- Módulo ausente, Android e web resultam em estado indisponível. Não utilizar mocks como fallback de captura real.

O processamento da sessão fica em fila serial fora da UI. Cada aquisição tem um único resultado e uma duração máxima de segurança, inclusive se não chegar nenhum frame. Timestamps inválidos, perda de autorização, interrupção, erro de sessão ou limite de coleção encerram a aquisição com estado controlado. Repetir captura não reaproveita timestamps ou frames anteriores.

## Verificação

- Testes TypeScript para resumo da aquisição e verificação sintética: timestamps adulterados, mapeamento incorreto, indisponibilidade e formato real rejeitado pelo contrato.
- Testes Swift do acumulador temporal: origem alta, monotonicidade, quatro segundos, limite de frames e reinicialização entre capturas; compilação do módulo para iOS.
- Checks existentes do monorepo e revisão independente de ciclo de vida/privacidade.
- Instalar build Release no mesmo iPhone, com assinatura serial e JavaScript embutido. Executar o teste sintético no Hermes e verificar os controles da câmera com o operador. Registrar o que foi observado diretamente e o que foi confirmado pelo operador.

## Referências

- Expo SDK 57: https://docs.expo.dev/versions/v57.0.0/
- Camera SDK 57: https://docs.expo.dev/versions/v57.0.0/sdk/camera/
- Módulos locais: https://docs.expo.dev/modules/get-started/
- AVFoundation output: https://developer.apple.com/documentation/avfoundation/avcapturevideodataoutput
- Frame drops: https://developer.apple.com/library/archive/technotes/tn2445/_index.html

## Estado

Revisão de planejamento concluída sem perguntas relevantes pendentes. Andrei aprovou explicitamente implementar a proposta e testar no iPhone nesta sessão. Os testes em Node do ciclo anterior não validam esta aquisição.
