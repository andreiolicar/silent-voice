# Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete simulated Silent Voice calibration flow, reusable from initial setup and the Hub, with typed domain state, deterministic development inspection, retry behavior, and no real hardware or persistence.

**Architecture:** Keep framework-independent calibration state in `src/domain/calibration`. Isolate all timers and inspection parameters in a feature-level mock/controller hook, then render one focused step at a time through reusable presentation components. Expose a routing-only `/calibration` entry and integrate it with Connection and Hub without adding a tab or global store.

**Tech Stack:** React Native, Expo SDK 57, TypeScript, Expo Router, React hooks, Lucide React Native, existing Silent Voice Design System.

**Spec:** `docs/superpowers/specs/2026-08-30-calibration-design.md`

## Global Constraints

- Do not implement real EMG, camera, USB, training, TinyML, MediaPipe, inference, persistence, backend, or a calibration gate in Live.
- Do not add dependencies, a global calibration store, a concrete hardware adapter, or a USB protocol.
- Keep the muscle mock sequence automatic: `waiting -> capturing -> processing -> success`.
- Do not render visible development controls or any touchscreen replacement for the physical button.
- Honor `step` and `state` inspection parameters only when `__DEV__` is true; keep `origin` functional.
- Preserve the current Design System, Safe Area behavior, responsive scrolling, accessibility, flat UI, and zero shadows.
- Do not consult or modify Figma.
- Do not commit or push before or after validation in this cycle.

## Rendered-check helper

Use this PowerShell helper for every rendered assertion because `Invoke-WebRequest` can expose UTF-8 response bytes through a Latin-1 string on Windows:

```powershell
$latin1 = [Text.Encoding]::GetEncoding(28591)
function Get-RenderedHtml([string]$Path) {
  $response = Invoke-WebRequest -UseBasicParsing -Uri ("http://localhost:8081" + $Path)
  if ($response.StatusCode -ne 200) { throw "$Path returned $($response.StatusCode)" }
  return [Text.Encoding]::UTF8.GetString($latin1.GetBytes($response.Content))
}
```

---

### Task 1: Establish rendered RED checks and calibration domain

**Files:**

- Create: `src/domain/calibration/calibration.types.ts`
- Create: `src/domain/calibration/index.ts`

**Interfaces:**

- Produces: `CalibrationStep`, `CalibrationCaptureState`, `CalibrationResultState`, `CalibrationResult`, `CalibrationOrigin`.
- Consumes: no framework or feature imports.

- [ ] **Step 1: Run the missing-route RED check**

With the Expo web server running on port 8081, request the planned route and assert the first-step copy:

```powershell
$html = Get-RenderedHtml '/calibration?origin=setup&step=preparation'
if (-not $html.Contains('Vamos calibrar seu Silent Voice')) { throw 'RED: calibration route/first step is not implemented' }
```

Expected: FAIL because `/calibration` does not exist.

- [ ] **Step 2: Add the framework-independent types**

```ts
export const calibrationSteps = [
  'preparation',
  'rest',
  'muscle',
  'visual',
  'validation',
  'complete',
] as const;

export type CalibrationStep = (typeof calibrationSteps)[number];

export const calibrationCaptureStates = [
  'idle',
  'waiting',
  'capturing',
  'processing',
  'success',
  'retry',
] as const;

export type CalibrationCaptureState = (typeof calibrationCaptureStates)[number];

export type CalibrationOrigin = 'hub' | 'setup';
export type CalibrationResultState = 'adequate' | 'captured' | 'pending';

export type CalibrationResult = {
  muscle: CalibrationResultState;
  rest: CalibrationResultState;
  visual: CalibrationResultState;
};
```

- [ ] **Step 3: Export the types from the domain package**

```ts
export {
  calibrationCaptureStates,
  calibrationSteps,
  type CalibrationCaptureState,
  type CalibrationOrigin,
  type CalibrationResult,
  type CalibrationResultState,
  type CalibrationStep,
} from './calibration.types';
```

- [ ] **Step 4: Verify domain compilation**

Run: `npm run typecheck`

Expected: PASS with no framework dependency in `src/domain/calibration`.

### Task 2: Centralize deterministic mock data and controller

**Files:**

- Create: `src/features/calibration/data/calibration.mock.ts`
- Create: `src/features/calibration/hooks/useMockCalibrationFlow.ts`

**Interfaces:**

- Consumes: domain calibration types.
- Produces:

```ts
resolveCalibrationOrigin(value): CalibrationOrigin;
resolveCalibrationInspection(stepValue, stateValue): CalibrationInspection | undefined;

type UseMockCalibrationFlowOptions = {
  inspectedState?: CalibrationCaptureState;
  inspectedStep?: CalibrationStep;
};

type MockCalibrationFlow = {
  captureState: CalibrationCaptureState;
  result: CalibrationResult;
  retryCurrentStep(): void;
  step: CalibrationStep;
  advance(): void;
};
```

- [ ] **Step 1: Run resolver/controller RED expectations**

The planned rendered URLs must currently fail to expose their isolated states:

```powershell
$checks = @(
  @{ path='/calibration?step=rest&state=retry'; text='Não conseguimos obter uma leitura estável.' },
  @{ path='/calibration?step=muscle&state=capturing'; text='Captando seu sinal...' },
  @{ path='/calibration?step=muscle&state=processing'; text='Analisando leitura...' },
  @{ path='/calibration?step=visual&state=success'; text='Boa visibilidade' }
)
foreach ($check in $checks) {
  $html = Get-RenderedHtml $check.path
  if (-not $html.Contains($check.text)) { throw "RED: $($check.path) missing $($check.text)" }
}
```

Expected: FAIL before the route and mock exist.

- [ ] **Step 2: Implement validated mock resolvers**

`calibration.mock.ts` must:

- normalize array query values to their first string;
- default invalid/missing origin to `hub`;
- return no inspection when `__DEV__` is false;
- accept only values from `calibrationSteps` and `calibrationCaptureStates`;
- provide copy/progress metadata without technical acquisition terms.

```ts
export type CalibrationInspection = {
  state?: CalibrationCaptureState;
  step: CalibrationStep;
};

export function resolveCalibrationOrigin(
  value: string | string[] | undefined,
): CalibrationOrigin;

export function resolveCalibrationInspection(
  stepValue: string | string[] | undefined,
  stateValue: string | string[] | undefined,
): CalibrationInspection | undefined;
```

- [ ] **Step 3: Implement the centralized automatic controller**

`useMockCalibrationFlow` must own the only calibration timers. Use one effect keyed by `step`, a restart version, and inspection presence. Schedule these state transitions:

```ts
const mockSequences = {
  rest: ['capturing', 'success'],
  muscle: ['waiting', 'capturing', 'processing', 'success'],
  visual: ['processing', 'success'],
  validation: ['processing', 'success'],
} as const;
```

Rules:

- preparation and complete do not schedule capture states;
- pinned inspection does not schedule or auto-navigate;
- successful validation advances to complete after its final delay;
- `advance()` moves only between allowed successful stages;
- `retryCurrentStep()` preserves prior results and increments a restart version;
- timers are cleared on cleanup;
- no query parameter or timer enters a domain type.

- [ ] **Step 4: Verify the controller compiles without native or persistence imports**

Run:

```powershell
npm run typecheck
rg -n -i 'UsbManager|AsyncStorage|MMKV|MediaPipe|TinyML|camera permission|Bluetooth|Wi-Fi' src/features/calibration src/domain/calibration
```

Expected: typecheck PASS and audit returns no implementation references.

### Task 3: Build reusable calibration presentation components

**Files:**

- Create: `src/features/calibration/components/CalibrationProgress.tsx`
- Create: `src/features/calibration/components/CalibrationCapturePanel.tsx`
- Create: `src/features/calibration/components/CalibrationVisualPanel.tsx`
- Create: `src/features/calibration/components/CalibrationResultRow.tsx`

**Interfaces:**

- Consumes: domain step/capture/result types and existing `AppText`, `Card`, `StatusBadge`, colors, radii, spacing.
- Produces:

```ts
type CalibrationProgressProps = { step: CalibrationStep };

type CalibrationCapturePanelProps = {
  description: string;
  state: CalibrationCaptureState;
  title: string;
  variant: 'muscle' | 'rest';
};

type CalibrationVisualPanelProps = {
  state: CalibrationCaptureState;
};

type CalibrationResultRowProps = {
  label: string;
  state: CalibrationResultState;
};
```

- [ ] **Step 1: Define component-level rendered expectations**

The future screen must include semantic progress and state-specific text:

```powershell
$html = Get-RenderedHtml '/calibration?step=rest&state=capturing'
@('Etapa 2 de 5','Fique em repouso','Captando referência...') | ForEach-Object {
  if (-not $html.Contains($_)) { throw "RED: missing $_" }
}
```

Expected: FAIL before the route/components exist.

- [ ] **Step 2: Implement `CalibrationProgress`**

Render a compact “Etapa N de 5” label plus five segments. Preparation through validation map to 1–5; completion marks all segments complete and uses the accessible label “Calibração concluída”. Segments use accent/background colors and do not rely on color alone because the textual stage count remains visible.

- [ ] **Step 3: Implement `CalibrationCapturePanel`**

Use one flat white Card for rest and muscle states. Map `state` to explicit text, icon, status tone, and deterministic linear progress. Retry renders the calm error copy; success renders the approved success copy. Do not render numerical signal data or a hardware-simulation button.

- [ ] **Step 4: Implement `CalibrationVisualPanel`**

Build an abstract frame with nested React Native Views and a module-camera icon. Map processing to “Ajustando enquadramento”, success to “Boa visibilidade”, and retry to “Reposicione o módulo”. Do not use `Image`, camera APIs, permissions, photographic placeholders, shadows, or scale motion.

- [ ] **Step 5: Implement `CalibrationResultRow`**

Render label plus the textual result `Aguardando`, `Capturado`, or `Adequado`, with a semantic icon and tone. Keep rows compact inside the validation Card.

- [ ] **Step 6: Verify component compilation and forbidden visual APIs**

Run:

```powershell
npm run typecheck
rg -n 'shadowColor|shadowOffset|shadowOpacity|shadowRadius|elevation|boxShadow|scale\(|translate' src/features/calibration/components
```

Expected: typecheck PASS and no shadow/transform matches.

### Task 4: Implement the focused calibration screen and route

**Files:**

- Create: `src/features/calibration/screens/CalibrationScreen.tsx`
- Create: `app/calibration.tsx`

**Interfaces:**

- Consumes: query resolvers, `useMockCalibrationFlow`, calibration components, `MainAppScreen`, `SystemAppHeader`, `Button`, `Card`, `AppText`.
- Produces: the `/calibration` route and all six step compositions.

- [ ] **Step 1: Create the routing-only file**

```ts
export { default } from '../src/features/calibration/screens/CalibrationScreen';
```

- [ ] **Step 2: Compose route state and navigation**

`CalibrationScreen` must:

```ts
const params = useLocalSearchParams<{
  origin?: string | string[];
  state?: string | string[];
  step?: string | string[];
}>();

const origin = resolveCalibrationOrigin(params.origin);
const inspection = resolveCalibrationInspection(params.step, params.state);
const flow = useMockCalibrationFlow({
  inspectedState: inspection?.state,
  inspectedStep: inspection?.step,
});
```

Use `MainAppScreen showBottomNavigation={false}` and `SystemAppHeader`. Back uses history when available; fallback is `/connection` for setup and `/hub` otherwise.

- [ ] **Step 3: Render Preparation**

Render the exact title and description from the cycle, the four checklist rows, the discreet discomfort guidance, and “Começar calibração”. The CTA calls `flow.advance()`.

- [ ] **Step 4: Render Rest and Muscle states**

Use `CalibrationCapturePanel`. Show “Continuar” only after success. Retry shows “Tentar novamente” and calls a screen handler that removes pinned `step/state` via `router.replace({ pathname: '/calibration', params: { origin } })` before restarting the mock. Muscle waiting/capturing/processing contains no visible development control.

- [ ] **Step 5: Render Visual and Validation states**

Visual uses the abstract panel and success/retry CTAs. Validation shows the three result rows and advances automatically to complete unless inspection pins it.

- [ ] **Step 6: Render Completion**

Render “Tudo pronto”, the approved two supporting lines, and the origin-specific button. Setup replaces with `/home`; Hub replaces with `/hub`.

- [ ] **Step 7: Run the first full GREEN route suite**

Check these deterministic compositions:

```powershell
$checks = @(
  @{ path='/calibration?origin=setup&step=preparation'; text='Vamos calibrar seu Silent Voice' },
  @{ path='/calibration?origin=setup&step=rest&state=capturing'; text='Captando referência...' },
  @{ path='/calibration?origin=setup&step=muscle&state=waiting'; text='Pressione e mantenha o botão do Silent Voice' },
  @{ path='/calibration?origin=setup&step=muscle&state=capturing'; text='Captando seu sinal...' },
  @{ path='/calibration?origin=setup&step=muscle&state=processing'; text='Analisando leitura...' },
  @{ path='/calibration?origin=hub&step=visual&state=success'; text='Boa visibilidade' },
  @{ path='/calibration?origin=hub&step=validation&state=processing'; text='Validando calibração' },
  @{ path='/calibration?origin=setup&step=complete'; text='Ir para início' },
  @{ path='/calibration?origin=hub&step=complete'; text='Voltar ao Hub' },
  @{ path='/calibration?origin=hub&step=rest&state=retry'; text='Tentar novamente' }
)
```

Expected: all paths return 200 and include their expected text.

### Task 5: Integrate setup and Hub navigation

**Files:**

- Modify: `src/features/initial-flow/screens/ConnectionScreen.tsx`
- Modify: `src/features/hub/screens/HubScreen.tsx`
- Modify: `src/features/hub/data/hub.mock.ts`

**Interfaces:**

- Consumes: `/calibration?origin=setup` and `/calibration?origin=hub`.
- Produces: complete first-setup and recalibration entry paths.

- [ ] **Step 1: Run navigation RED checks**

Inspect source/rendered output before changes:

```powershell
rg -n "POST_CONNECTION_ROUTE = '/calibration\?origin=setup'|calibration: \(\) => router.push\('/calibration\?origin=hub'\)" src/features
```

Expected: no matches.

- [ ] **Step 2: Redirect successful connection into setup calibration**

Change only:

```ts
const POST_CONNECTION_ROUTE = '/calibration?origin=setup' as const;
```

Both automatic success navigation and the connected-state Continue action already consume this constant and therefore remain consistent.

- [ ] **Step 3: Activate the Hub resource**

Add:

```ts
calibration: () => router.push('/calibration?origin=hub'),
```

Change its description to the approved copy:

```ts
description: 'Ajuste a leitura dos seus sinais.',
```

- [ ] **Step 4: Verify navigation integration and no tab registration**

Run:

```powershell
rg -n "calibration\?origin=(setup|hub)" src/features
rg -n "calibration" src/components/layout/BottomNavigation.tsx
```

Expected: setup and Hub routes are present; BottomNavigation has no calibration item.

### Task 6: Validate retry, accessibility, responsive layout, and architecture boundaries

**Files:**

- Review: `src/features/calibration/**`
- Review: `app/calibration.tsx`

**Interfaces:**

- Produces: final accessible/responsive feature with no forbidden capability claims.

- [ ] **Step 1: Validate all retry compositions**

Render retry for rest, muscle, and visual:

```text
/calibration?step=rest&state=retry
/calibration?step=muscle&state=retry
/calibration?step=visual&state=retry
```

Each must show the stable-reading message and “Tentar novamente”; none may show success or advance automatically while pinned.

- [ ] **Step 2: Validate accessibility semantics**

Inspect rendered accessibility labels for:

- back button;
- “Etapa N de 5”/completed progress;
- checklist state;
- capture state;
- visual state;
- result rows;
- retry and completion actions.

No state may be communicated only through color.

- [ ] **Step 3: Validate visual layouts**

Capture and inspect preparation, rest, muscle, visual, validation, complete, and retry at approximately 402 × 874. Repeat preparation, muscle, and validation at a reduced height such as 402 × 700.

Confirm:

- content scrolls and CTA remains reachable;
- no BottomNavigation is present;
- Safe Area/header/content do not overlap;
- only one main stage is visible;
- cards, spacing, typography, radii, and colors match existing screens;
- no shadows, scale, translate, fake camera feed, or technical dashboard appear.

- [ ] **Step 4: Audit forbidden copy and implementation**

Run:

```powershell
rg -n -i 'ADC|RAW|ENV|threshold|landmarks|feature extraction|dataset|precisão garantida|100% calibrado|reconhecimento perfeito|OpenMV|Bluetooth|Wi-Fi|IMU|UsbManager|AsyncStorage|MMKV|MediaPipe|TinyML' app/calibration.tsx src/features/calibration src/domain/calibration
```

Expected: no matches in the calibration implementation.

### Task 7: Run final technical verification and inspect the diff

**Files:**

- Review: entire working tree.

**Interfaces:**

- Produces: evidence for the completion report.

- [ ] **Step 1: Run all required project checks**

```powershell
npm run lint
npm run typecheck
npm run format:check
npx expo install --check
npx expo-doctor
git diff --check
```

Expected: every command exits 0; Expo Doctor reports all checks passed.

- [ ] **Step 2: Re-run the complete rendered acceptance suite**

Render the normal route, all five operational steps, completion for both origins, and retry for each capture stage. Verify prohibited UI text and BottomNavigation are absent.

- [ ] **Step 3: Review the final scope**

```powershell
git status --short
git diff --stat
git diff -- app/calibration.tsx src/domain/calibration src/features/calibration src/features/initial-flow/screens/ConnectionScreen.tsx src/features/hub/screens/HubScreen.tsx src/features/hub/data/hub.mock.ts docs/superpowers
```

Confirm no dependency/configuration/native/hardware/persistence changes and no files outside the approved cycle.

- [ ] **Step 4: Prepare the completion report without Git mutation**

Report flow, navigation, domain, rest, muscle, visual, retry, completion, mock inspection URLs, Design System adherence, complete validation results, main files, and only real future hardware dependencies. Do not commit or push.
