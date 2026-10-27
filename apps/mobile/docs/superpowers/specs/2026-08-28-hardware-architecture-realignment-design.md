# Ciclo 6.1 — Realinhamento da Arquitetura de Hardware

## Objetivo

Alinhar o mobile ao caminho físico `MyoWare 2 → ESP32-S3 → Raspberry Pi Zero 2 W → USB → Galaxy A17`, mantendo o `SilentVoiceDevice` como boundary e sem implementar USB nativo ou escolher protocolo antes do ensaio físico.

## Boundary e transporte

- `DeviceTransport` possui somente `'usb'`.
- `DeviceConnectionState` representa `disconnected`, `waitingForUsb`, `detected`, `authorizationRequired`, `connecting`, `connected` e `failed`.
- `SilentVoiceDevice` continua sendo o contrato consumido pelo aplicativo.
- `MockSilentVoiceDevice` permanece como implementação de desenvolvimento.
- `UsbSilentVoiceDevice` é apenas a direção arquitetural futura documentada; não haverá classe, driver, `UsbManager`, serial, HTTP, WebSocket ou protocolo próprio neste ciclo.
- O parâmetro `?state=` pertence exclusivamente ao mock da tela de conexão. Ele não entra no contrato do device nem em um futuro adapter real.

## Modelo de hardware

A visão operacional usa seis subsistemas essenciais centralizados no mock de system overview:

1. Raspberry Pi Zero 2 W — gateway físico e conexão USB com o Android.
2. ESP32-S3 — aquisição e processamento inicial de EMG.
3. MyoWare 2 — sensor neuromuscular.
4. Câmera OV5647 — visão conectada ao Raspberry por CSI.
5. INMP441 — contexto sonoro conectado por I²S.
6. Saída de áudio — MAX98357A e alto-falante.

A Home deriva `6/6` dessa lista. RSSI e percentuais de bateria são removidos porque não representam telemetria disponível. Saúde do sistema usa alimentação estável, temperatura, latência e uso do Raspberry, aceitando valores indisponíveis no tipo.

## Fluxo inicial

- Onboarding 3 comunica processamento local/offline, cabo e controle dos dados.
- Permissões mostra Notificações como opção e Dispositivo USB como informação. USB não é toggle e sua autorização é solicitada pelo Android somente quando o hardware for conectado, em ciclo futuro.
- Conexão deixa de descobrir dispositivos Bluetooth. O mock demonstra os seis estados USB por progressão automática ou por `?state=<estado>` para inspeção determinística. Estados fixados pela query não avançam nem navegam automaticamente.

## Comunicação ao vivo

O fluxo passa a ser `idle → ready → capturing → decoding → candidate → validating → confirmed → speaking → ready`. O app inicia ou encerra a sessão; o botão físico autoriza a captura enquanto pressionado. A UI não simula o botão como ação de tela e apenas explica os estados.

A camada interna `mechanical` é substituída por `physicalAuthorization`. As demais são `neuromuscular`, `visual`, `contextual` e `decision`; nenhuma é exibida na tela principal. O contexto dos últimos 10 segundos continua vindo conceitualmente do INMP441 através do Raspberry.

## UI e Design System

As telas mantêm estrutura, tipografia, espaçamentos, cards, navbar e linguagem flat. O card USB não usa glow. Assets antigos não serão apagados automaticamente; apenas deixarão de representar arquitetura ou nomenclatura atual.

## Validação

Antes das alterações, checks de rota devem falhar ao procurar estados/copy USB e o novo fluxo físico. Depois, as rotas `/permissions`, `/connection?state=...`, `/home`, `/modules`, `/system-health`, `/hub`, `/live?phase=...`, `/onboarding/3` e `/playground` devem renderizar os conceitos novos. A auditoria global não pode encontrar arquitetura atual baseada em BLE, Wi-Fi, IMU, OpenMV, Neckband, AirPods, RSSI ou camada Mecânica.

## Pendência física deliberada

O protocolo entre Galaxy A17 e Raspberry Pi Zero 2 W permanece não definido até o ensaio físico. Também permanecem fora do ciclo a autorização USB real, transporte de telemetria e retorno de áudio sintetizado ao módulo.
