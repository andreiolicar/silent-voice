# Calibration Design

## Goal

Implement a complete simulated calibration experience that teaches the Silent Voice to recognize each user's individual signals without exposing acquisition details or implying that real hardware, inference, training, or persistence already exists.

The flow reuses one feature for initial setup and future recalibration from the Hub.

## Scope and constraints

This cycle includes the route, typed calibration state, development mock, guided UI, navigation integration, deterministic inspection, retry behavior, accessibility, responsiveness, and validation.

It does not include real EMG, camera, USB, model training, TinyML, MediaPipe, inference, persistence, backend, or a Live-session calibration gate. It does not add a global store or define a hardware protocol.

The physical architecture remains:

```text
MyoWare 2 -> ESP32-S3 -> Raspberry Pi Zero 2 W -> USB -> Android
```

The Android app does not access the MyoWare, ESP32-S3, or camera directly.

## Route and origins

The feature is exposed at `/calibration` outside the tab routes because it is a focused flow and must not show `BottomNavigation`.

The functional `origin` parameter determines only entry/exit navigation:

- `/calibration?origin=setup`: entered after the first successful mock USB connection; completion replaces the route with `/home`.
- `/calibration?origin=hub`: entered from the Hub resource; completion replaces the route with `/hub`.
- Missing or invalid origin defaults to `hub`, which is the safer direct-entry behavior.

Back navigation uses router history when available. The fallback is `/connection` for setup and `/hub` for recalibration. Leaving early does not mark calibration as complete.

## Domain model

Framework-independent calibration types live under `src/domain/calibration`:

```ts
type CalibrationStep =
  'preparation' | 'rest' | 'muscle' | 'visual' | 'validation' | 'complete';

type CalibrationCaptureState =
  'idle' | 'waiting' | 'capturing' | 'processing' | 'success' | 'retry';

type CalibrationResultState = 'pending' | 'captured' | 'adequate';

type CalibrationResult = {
  rest: CalibrationResultState;
  muscle: CalibrationResultState;
  visual: CalibrationResultState;
};
```

The exact implementation can refine names while preserving these semantics. Domain types do not include timers, query parameters, touchscreen simulation controls, native USB concepts, or concrete sensor data.

## Mock controller

All timing and simulated acquisition behavior is centralized in the calibration feature rather than distributed across step components.

The mock controller owns the current step, capture state, progress, results, retry, and transitions. UI components receive already-resolved state and callbacks. This creates a clean replacement point for a future real calibration coordinator without changing the presentation model or introducing a premature hardware interface now.

Natural development flow:

```text
preparation --CTA--> rest
rest: capturing -> success --CTA--> muscle
muscle: waiting -> capturing -> processing -> success --CTA--> visual
visual: processing -> success --CTA--> validation
validation: processing -> success -> complete
```

The muscle sequence is fully automatic. No visible “Iniciar simulação”, “Pressionar botão físico”, debug action, or touchscreen substitute is rendered. The copy explains that the physical Silent Voice button authorizes capture; the mock merely emits those states during development.

Retries restart only the current step. A retry state never advances silently.

## Deterministic development inspection

`origin` is a functional parameter. `step` and `state` are development-only inspection parameters:

```text
/calibration?origin=setup&step=preparation
/calibration?origin=setup&step=rest&state=capturing
/calibration?origin=setup&step=rest&state=retry
/calibration?origin=hub&step=muscle&state=waiting
/calibration?origin=hub&step=muscle&state=processing
/calibration?origin=hub&step=visual&state=success
/calibration?origin=hub&step=validation&state=processing
/calibration?origin=hub&step=complete
```

Resolvers accept only known domain values and only honor `step` and `state` when `__DEV__` is true. When an inspection value pins the composition, automatic timers and automatic navigation are disabled. No debug controls appear in the interface, and production behavior ignores these inspection parameters.

## Screen structure

`CalibrationScreen` uses `MainAppScreen` with `showBottomNavigation={false}` and `SystemAppHeader` with back navigation. The content remains scrollable and follows the existing 402 px maximum-width shell.

The screen contains:

1. Header.
2. Compact `CalibrationProgress` for the five operational stages.
3. One primary stage composition at a time.
4. Contextual action when the current stage permits user advancement.

Preparation through validation are shown as “Etapa N de 5”. Completion is a separate terminal composition and presents the progress as complete without inventing a sixth operational stage.

## Stage compositions

### Preparation

- “Vamos calibrar seu Silent Voice”.
- Explains that calibration helps recognize personal signals more accurately.
- Checklist: module connected, sensor positioned, camera directed toward the mouth, comfortable environment.
- Discreet safety guidance: stop if there is discomfort.
- CTA: “Começar calibração”.

The sensor copy does not claim a universal placement.

### Rest

- “Fique em repouso”.
- Instructs the user to relax the face and avoid attempting speech briefly.
- Uses a simple linear progress treatment.
- Shows “Captando referência...” followed by “Referência capturada”.
- Does not expose signal values or acquisition terminology.

### Muscle signal

- “Agora tente falar”.
- Instructs the user to press and hold the physical Silent Voice button while making the speech movement.
- Automatic mock sequence:
  - waiting: ready for the physical action;
  - capturing: “Captando seu sinal...”;
  - processing: “Analisando leitura...”;
  - success: “Sinal reconhecido”.
- Does not render any action that impersonates the physical button.

### Mouth movement

- “Movimento da boca”.
- Instructs the user to look forward and repeat the requested speech movement.
- Uses an abstract framing composition built with React Native views and icons.
- Shows adjusting, good visibility, or reposition guidance without asserting real facial detection.
- Does not open the phone camera, request camera permission, or render a photographic feed.

### Validation

- “Validando calibração”.
- Compact result rows for Rest, Muscle signal, and Mouth movement.
- Values are Captured, Captured, and Adequate once successful.
- A short automatic progression leads to the terminal composition.

### Completion

- “Tudo pronto”.
- “Seu Silent Voice está calibrado para começar.”
- Explains that recalibration can be repeated later.
- `setup` CTA: “Ir para início”.
- `hub` CTA: “Voltar ao Hub”.

The UI does not promise guaranteed accuracy, perfect recognition, or a percentage of calibration quality.

## Retry behavior

Rest, muscle, and visual acquisition states can resolve to retry in the development mock. Retry shows a non-alarmist message such as “Não conseguimos obter uma leitura estável.” and the CTA “Tentar novamente”.

The CTA clears a pinned development state from the route when necessary, restarts the current mock sequence, and preserves completed results from earlier stages. It does not reset the entire calibration unless the user leaves the flow.

## Components

The feature may add these focused presentation components:

- `CalibrationProgress`: accessible stage count and compact segmented indicator.
- `CalibrationCapturePanel`: shared state presentation for rest and muscle capture.
- `CalibrationVisualPanel`: abstract module-camera framing state.
- `CalibrationResultRow`: compact validation summary.

Components reuse `Screen`, `AppText`, `Button`, `Card`, `StatusBadge`, current colors, typography, spacing, and radii. No general-purpose abstraction is added unless a second consumer exists.

## Visual and responsive behavior

The screen preserves the Silent Voice visual language: `#F6F5F8` background, white cards, navy text, green accent, Manrope, existing radii, flat surfaces, and zero shadows.

Only subtle progress, opacity, and state transitions are used. There is no bounce, decorative motion, large loader, scale, or translation. Reduced-motion preferences are respected through existing motion utilities when animation is used.

The content scrolls on reduced heights. Safe Area remains active, the CTA stays reachable through scrolling, and no absolute positioning is used except within the genuinely layered abstract framing illustration.

States include text and semantic labels, so meaning never depends on color alone. Interactive targets use existing accessible button/header components.

## Navigation integration

- Add the routing-only file `app/calibration.tsx`.
- Change the successful connection destination from `/home` to `/calibration?origin=setup`.
- Add the Hub resource action for `/calibration?origin=hub`.
- Update the Hub description to “Ajuste a leitura dos seus sinais.”.
- Do not add a tab item or a Home card.
- Do not change Live behavior or add a global calibration store.

## Validation strategy

Before implementation, rendered route checks must fail for the missing calibration route, stage copy, deterministic states, retry, and Hub/setup navigation targets.

After implementation:

- Render preparation, rest, muscle, visual, validation, completion, and retry states through development query parameters.
- Verify setup and Hub exit labels and destinations.
- Verify obsolete or prohibited terms and visible debug controls are absent.
- Inspect the seven required compositions near 402 × 874 and at a reduced height.
- Confirm BottomNavigation is absent.
- Run `npm run lint`, `npm run typecheck`, `npm run format:check`, `npx expo install --check`, `npx expo-doctor`, and `git diff --check`.

No commit or push is performed in this cycle.

## Real future dependencies

Physical signal acquisition, physical-button events, camera framing evaluation, calibration algorithms, persistence, and the USB adapter remain future work dependent on hardware validation. These are not represented as implemented capabilities in the current UI.
