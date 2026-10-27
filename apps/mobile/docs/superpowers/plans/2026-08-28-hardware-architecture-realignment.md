# Hardware Architecture Realignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Realinhar domínio, mocks, telas e documentação do Silent Voice Mobile para Raspberry Pi Zero 2 W via USB e autorização física de fala.

**Architecture:** Atualizar primeiro os contratos puros, depois os mocks centralizados e por fim seus consumidores visuais. A inspeção `?state=` fica confinada ao mock de conexão; nenhum adapter USB concreto será criado.

**Tech Stack:** React Native, Expo SDK 57, TypeScript, Expo Router, Zustand e componentes existentes do Design System.

**Spec:** `docs/superpowers/specs/2026-08-28-hardware-architecture-realignment-design.md`

## Global Constraints

- Não implementar Android USB Host API, `UsbManager`, driver, serial, HTTP, WebSocket ou protocolo USB.
- Não adicionar BLE, Wi-Fi, IMU, OpenMV, RSSI ou percentuais de power bank à arquitetura atual.
- Manter Expo SDK 57 e as dependências existentes.
- Preservar Design System, layouts aprovados, flat UI e zero shadows.
- Não apagar assets sem verificar referências.
- Não fazer commit nem push.

---

### Task 1: Contratos de dispositivo e conexão

**Files:**

- Modify: `src/domain/device/device.types.ts`
- Modify: `src/domain/device/SilentVoiceDevice.ts`
- Modify: `src/domain/device/index.ts`
- Modify: `src/stores/device.store.ts`

**Interfaces:**

- Produces: `DeviceTransport = 'usb'`, estados USB e sessão com autorização física.

```ts
export type DeviceTransport = 'usb';
export type DeviceConnectionState =
  | 'disconnected'
  | 'waitingForUsb'
  | 'detected'
  | 'authorizationRequired'
  | 'connecting'
  | 'connected'
  | 'failed';
```

- [ ] Executar um smoke check renderizado que falha para `/connection?state=waitingForUsb` e `/live?phase=ready`.
- [ ] Substituir estados BLE por estados USB e atualizar o estado inicial da store para `disconnected`.
- [ ] Preservar `SilentVoiceDevice` sem métodos de protocolo ou APIs nativas.
- [ ] Executar `npm run typecheck` para listar consumidores que precisam ser migrados.

### Task 2: Fluxo inicial USB e privacidade

**Files:**

- Modify: `src/features/initial-flow/components/PermissionCard.tsx`
- Modify: `src/features/initial-flow/screens/PermissionsScreen.tsx`
- Modify: `src/features/initial-flow/screens/ConnectionScreen.tsx`
- Modify: `src/features/initial-flow/screens/OnboardingThreeScreen.tsx`
- Modify: `src/components/silent-voice/DeviceCard.tsx`

**Interfaces:**

- Consumes: `DeviceConnectionState`.
- Produces: `resolveMockConnectionState()` e UI informativa USB sem toggle.

```ts
type PermissionCardProps =
  | { variant: 'toggle'; enabled: boolean; onChange: (value: boolean) => void }
  | { variant: 'informational'; enabled?: never; onChange?: never };

const connectionStateCopy: Record<
  DeviceConnectionState,
  {
    title: string;
    description: string;
    tone: 'neutral' | 'success' | 'error';
  }
> = {
  disconnected: {
    title: 'Desconectado',
    description: 'Inicie a preparação da conexão.',
    tone: 'neutral',
  },
  waitingForUsb: {
    title: 'Aguardando cabo',
    description: 'Conecte o cabo de dados USB ao celular.',
    tone: 'neutral',
  },
  detected: {
    title: 'Dispositivo detectado',
    description: 'Módulo Silent Voice encontrado.',
    tone: 'success',
  },
  authorizationRequired: {
    title: 'Aguardando autorização',
    description: 'Confirme o acesso quando o sistema solicitar.',
    tone: 'neutral',
  },
  connecting: {
    title: 'Conectando',
    description: 'Preparando a conexão USB.',
    tone: 'neutral',
  },
  connected: {
    title: 'Conectado',
    description: 'Módulo Silent Voice conectado por USB.',
    tone: 'success',
  },
  failed: {
    title: 'Falha na conexão',
    description: 'Verifique o cabo e tente novamente.',
    tone: 'error',
  },
};
```

- [ ] Fazer o check RED confirmar ausência de “Dispositivo USB” e “Aguardando cabo”.
- [ ] Adicionar modo `toggle | informational` ao `PermissionCard` e renderizar somente Notificações + Dispositivo USB.
- [ ] Implementar os seis estados visuais da conexão; query fixa o estado e o fluxo sem query avança deterministicamente.
- [ ] Simplificar `DeviceCard` para o módulo USB, removendo external devices, RSSI, bateria e glow.
- [ ] Atualizar a copy do Onboarding 3 para local, offline e cabo.
- [ ] Fazer o check GREEN renderizar cada estado por query.

### Task 3: Catálogo operacional, Home e módulos

**Files:**

- Modify: `src/features/system-overview/data/system-overview.mock.ts`
- Modify: `src/features/system-overview/screens/HomeScreen.tsx`
- Modify: `src/features/system-overview/screens/ModulesScreen.tsx`
- Modify: `src/components/silent-voice/ModuleCard.tsx`

**Interfaces:**

- Produces: seis `SystemModule`, `requiredModuleSummary` derivado e métricas sem telemetria inventada.

```ts
export type SystemModuleId =
  'raspberryPi' | 'esp32' | 'myoware' | 'camera' | 'inmp441' | 'audioOutput';

const requiredModuleSummary = {
  connected: systemModulesMock.filter((module) => module.state === 'connected')
    .length,
  total: systemModulesMock.length,
};
```

- [ ] Fazer o check RED falhar para `USB`, `6/6` e os seis nomes atuais.
- [ ] Substituir o catálogo antigo pelos seis subsistemas aprovados e metadados simples de função/interface.
- [ ] Derivar o resumo da Home e trocar Bateria por Alimentação/Estável.
- [ ] Remover RSSI e bateria das props/renderização de `ModuleCard`.
- [ ] Fazer o check GREEN nas rotas `/home` e `/modules`.

### Task 4: Saúde e Hub orientados ao Raspberry

**Files:**

- Modify: `src/features/system-overview/data/system-overview.mock.ts`
- Modify: `src/features/system-overview/screens/SystemHealthScreen.tsx`
- Modify: `src/features/system-overview/components/HealthMetricCard.tsx`
- Modify: `src/features/hub/components/HubDeviceCard.tsx`
- Modify: `src/features/hub/data/hub.mock.ts`
- Modify: `src/features/hub/screens/HubScreen.tsx`

**Interfaces:**

- Consumes: gateway Raspberry e transporte USB.
- Produces: saúde com valores conhecidos ou indisponíveis e Hub sem percentual de bateria.

```ts
export type HealthMetricValue =
  { state: 'available'; text: string } | { state: 'unknown' | 'unavailable' };

export const hubDeviceMock = {
  connected: true,
  name: 'Módulo Silent Voice',
  gateway: 'Raspberry Pi Zero 2 W',
  transport: 'USB',
} as const;
```

- [ ] Fazer o check RED falhar para “Alimentação”, “Uso Raspberry Pi” e “Módulo Silent Voice”.
- [ ] Atualizar saúde para alimentação, temperatura, latência e uso do Raspberry.
- [ ] Modelar valor de saúde como string ou estado `unknown | unavailable`, com label acessível.
- [ ] Atualizar Hub para Módulo Silent Voice, USB e Raspberry, usando ícone de cabo/USB.
- [ ] Fazer o check GREEN em `/system-health` e `/hub`.

### Task 5: Sessão ao vivo com autorização física

**Files:**

- Modify: `src/features/live-communication/types/live-session.ts`
- Modify: `src/features/live-communication/data/live-session.mock.ts`
- Modify: `src/features/live-communication/components/LiveInterpretationCard.tsx`
- Modify: `src/features/live-communication/screens/LiveCommunicationScreen.tsx`

**Interfaces:**

- Produces: fases `ready` e `capturing`, camada `physicalAuthorization` e resolução determinística por `?phase=`.

```ts
export type LiveSessionPhase =
  | 'idle'
  | 'ready'
  | 'capturing'
  | 'decoding'
  | 'candidate'
  | 'validating'
  | 'confirmed'
  | 'speaking'
  | 'needsRetry'
  | 'error';

export type ValidationLayerId =
  | 'physicalAuthorization'
  | 'neuromuscular'
  | 'visual'
  | 'contextual'
  | 'decision';
```

- [ ] Fazer o check RED falhar para as fases `ready` e `capturing`.
- [ ] Substituir `listening` por `ready`/`capturing` e `mechanical` por `physicalAuthorization`.
- [ ] Atualizar mock, status, retry e ação iniciar/parar sem simular o botão físico na tela.
- [ ] Preservar contexto dos últimos 10 segundos e histórico da sessão.
- [ ] Fazer o check GREEN em `/live?phase=ready` e `/live?phase=capturing`.

### Task 6: Playground e documentação

**Files:**

- Modify: `src/features/playground/DesignSystemPlaygroundScreen.tsx`
- Modify: `docs/architecture.md`
- Modify: `docs/design-system.md`
- Modify: `AGENTS.md`

**Interfaces:**

- Consumes: componentes já migrados.
- Produces: exemplos e regras que não reintroduzem a arquitetura antiga.

```text
MyoWare 2 -> ESP32-S3 -> Raspberry Pi Zero 2 W -> USB -> Galaxy A17
Galaxy A17 -> síntese de voz -> Raspberry Pi Zero 2 W -> MAX98357A -> alto-falante
```

- [ ] Migrar playground para dispositivo USB, alimentação e módulo sem RSSI/bateria.
- [ ] Documentar os dois fluxos físicos e o protocolo ainda não definido.
- [ ] Substituir orientação de BLE por futuro `UsbSilentVoiceDevice` no `AGENTS.md`.
- [ ] Remover a exceção de glow obsoleta da documentação visual.

### Task 7: Auditoria e validação final

**Files:**

- Review: todo o repositório, excluindo dependências, build e histórico Git.

**Interfaces:**

- Produces: diff auditado e evidência de validação.

```powershell
rg -n -i --hidden -g '!node_modules/**' -g '!.git/**' -g '!.expo/**' -g '!dist/**' "BLE|Bluetooth|Wi-Fi|WiFi|IMU|MPU6050|OpenMV|Neckband|AirPods|RSSI|mechanical|Mecânica" .
npm run lint
npm run typecheck
npm run format:check
npx expo install --check
npx expo-doctor
git diff --check
```

- [ ] Rodar a auditoria global dos termos obsoletos e classificar cada ocorrência restante.
- [ ] Verificar referências antes de manter ou remover assets antigos; não apagar apenas por nome.
- [ ] Validar visualmente as oito telas e todos os estados USB via query.
- [ ] Executar `npm run lint`, `npm run typecheck`, `npm run format:check`, `npx expo install --check`, `npx expo-doctor` e `git diff --check`.
- [ ] Confirmar que não houve commit nem push e preparar o relatório do ciclo.
