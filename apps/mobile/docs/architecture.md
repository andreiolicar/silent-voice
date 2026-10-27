# Arquitetura

## Stack

React Native com Expo SDK 57, TypeScript estrito, Expo Router, Zustand, React Native Safe Area Context, Expo Font e Manrope. O projeto permanece no fluxo managed do Expo.

## Organização

- `app/`: entradas finas de rota e composição global do Expo Router.
- `src/components/ui/`: primitivas visuais genéricas do Design System.
- `src/components/layout/`: estrutura de tela, cabeçalhos e navegação.
- `src/components/silent-voice/`: padrões visuais do produto.
- `src/domain/`: contratos e tipos independentes de UI e infraestrutura.
- `src/stores/`: stores Zustand pequenas e orientadas por responsabilidade.
- `src/theme/`: tokens visuais centralizados.
- `src/features/`: módulos verticais dos fluxos do produto.
- `src/services/`: adapters concretos somente quando a integração física for autorizada por um ciclo específico.

## Arquitetura física atual

O caminho de aquisição e decisão do MVP é:

```text
MyoWare 2
  -> RAW + ENV
ESP32-S3
  -> aquisição EMG, processamento inicial e timestamps
  -> UART 3,3 V + pulso físico de sincronização
Raspberry Pi Zero 2 W
  -> gateway, sincronização multimodal, câmera, contexto sonoro e controles
  -> USB por cabo
Samsung Galaxy A17
  -> modelos locais, fusão, decisão, síntese de voz e aplicativo
```

O aplicativo Android conversa somente com o Raspberry Pi Zero 2 W. ESP32-S3, MyoWare 2, câmera OV5647 e INMP441 ficam atrás desse gateway.

O caminho planejado de reprodução é:

```text
Android -> síntese de voz -> Raspberry Pi Zero 2 W -> MAX98357A -> alto-falante
```

O protocolo de dados e áudio sobre USB ainda não foi definido e depende de ensaio físico. O mobile não contém Android USB Host API, `UsbManager`, serial, HTTP, WebSocket, ADB, TCP ou protocolo próprio.

## Limite do dispositivo

A aplicação depende de `SilentVoiceDevice`, nunca de uma API nativa diretamente.

```text
UI / feature -> SilentVoiceDevice <- MockSilentVoiceDevice
                                  <- UsbSilentVoiceDevice (futuro)
```

`DeviceTransport` contém apenas `usb`. A conexão é modelada como espera pelo cabo, detecção, autorização, conexão, estado conectado ou falha. O parâmetro `?state=` da tela de conexão existe somente no mock para inspeção determinística e não pertence ao contrato de um futuro adapter.

`UsbSilentVoiceDevice` não está implementado. A autorização Android vinculada ao dispositivo e o protocolo definitivo serão definidos após validação física.

## Hardware operacional

Os seis subsistemas essenciais representados no aplicativo são:

- Raspberry Pi Zero 2 W (SC0721), gateway físico;
- ESP32-S3-DEV-KIT-N16R8-M (Waveshare 28836);
- MyoWare 2 Muscle Sensor (DEV-27924);
- câmera OV5647 de 5 MP (MakerHero DRA28), conectada por CSI;
- INMP441 (MakerHero 4MDR3), conectado por I²S;
- saída de áudio MAX98357A (Adafruit 3006) e alto-falante YSD 4 Ω / 3 W.

A Home deriva a contagem operacional dessa lista. RSSI e percentuais dos power banks não fazem parte do modelo porque não existe fonte de telemetria validada.

## Autorização física da fala

O botão Metaltex AV16FA autoriza fisicamente cada tentativa:

```text
pressionar e manter -> ready -> capturing
soltar -> decoding -> candidate -> validating -> confirmed -> speaking -> ready
```

O botão do aplicativo inicia ou encerra a sessão; ele não substitui o acionamento físico. A validação interna reconhece `physicalAuthorization`, `neuromuscular`, `visual`, `contextual` e `decision`, sem expor essas camadas ao usuário comum.

## Contexto e processamento local

O contexto ambiental vem do INMP441 via I²S para o Raspberry, entra em um buffer móvel de 10 segundos e chega ao Android separado do Histórico. O aplicativo não solicita o microfone do Galaxy para essa função.

Interpretação e síntese são locais e offline no Android. Não há backend, armazenamento remoto ou processamento em nuvem modelado no MVP atual.

## Mocks e telemetria

Conexão, módulos, saúde e sessão ao vivo permanecem determinísticos e demonstrativos. Métricas de saúde aceitam valores disponíveis, desconhecidos ou indisponíveis; nenhum mock deve se tornar requisito obrigatório de telemetria para o hardware real.
