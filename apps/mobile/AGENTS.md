# Silent Voice Mobile — Agent Instructions

## Project

Silent Voice Mobile is the React Native application for the Silent Voice assistive communication system.

Root:
`C:\Users\USER\Desktop\silent-voice-mobile`

## Stack

- React Native
- Expo SDK 57
- TypeScript
- Expo Router
- Zustand
- React Native Safe Area Context
- Manrope
- ESLint
- Prettier

Do not introduce Tailwind, NativeWind, or heavy UI frameworks unless explicitly requested.

## Expo

Expo changes frequently.

Before making decisions involving Expo APIs, configuration, native modules, builds, permissions, or package compatibility, read the exact SDK 57 documentation:

https://docs.expo.dev/versions/v57.0.0/

Do not upgrade Expo or major dependencies unless explicitly requested.

## Architecture

Preserve the existing architecture and separation of responsibilities.

Main areas:

- `app/`: routing only
- `src/components/`: reusable presentation
- `src/features/`: feature-specific code
- `src/domain/`: framework-independent domain contracts and types
- `src/services/`: infrastructure/services
- `src/stores/`: Zustand state
- `src/theme/`: design tokens
- `docs/`: architectural decisions

Avoid unnecessary abstractions, duplication, and speculative infrastructure.

## Hardware Boundary

Application features must not depend directly on native USB APIs or hardware libraries.

Interaction with Silent Voice hardware must occur through domain contracts such as `SilentVoiceDevice`.

The current hardware path is:

```text
MyoWare 2 -> ESP32-S3 -> Raspberry Pi Zero 2 W -> USB cable -> Android
```

The Raspberry Pi Zero 2 W is the physical gateway. Android communicates only with this gateway through the planned USB connection.

Future implementations may include:

- `MockSilentVoiceDevice`
- `UsbSilentVoiceDevice`

The USB protocol is not defined yet. Do not implement Android USB Host APIs, native drivers, serial transport, or a concrete `UsbSilentVoiceDevice` unless a future cycle explicitly requests it after physical validation.

Do not reintroduce BLE, Wi-Fi, IMU, or direct application dependencies on ESP32-S3, MyoWare, camera, or INMP441 without an explicit architecture decision.

## Design System

The code Design System is the structural source of truth.

Figma is the visual source of truth.

Existing Figma file:

- File: `Wireframe - Aplicativo Silent Voice`
- File key: `spBEx7SnMebeWHtJQWsDVh`
- Mobile page: `0:1`
- Components: `107:1820`

When implementing an existing Figma screen:

1. Inspect the specific frame through Figma MCP.
2. Use `get_design_context`.
3. Treat generated React/Tailwind only as visual/reference information.
4. Convert the design properly to React Native.
5. Reuse existing project components and tokens.
6. Do not copy Tailwind or generated web code.
7. Normalize accidental inconsistencies in spacing, typography, radius, sizing, and component structure.
8. Preserve the Silent Voice visual identity.

New screens that do not yet exist in Figma must follow the same established Design System.

## Visual Consistency

Do not reproduce accidental inconsistencies from the wireframe.

Prefer established tokens and recurring patterns for:

- spacing
- padding
- gaps
- typography
- font weights
- border radius
- colors
- component dimensions

If two visually equivalent elements differ slightly in Figma, use the established code standard unless the difference is clearly intentional.

## Responsive Layout

The Figma reference size is approximately `402 × 874`.

Never treat this as a fixed viewport.

Prefer:

- Flexbox
- Safe Area
- relative/full available width
- shared screen padding
- natural content sizing

Avoid absolute positioning unless required for a genuinely layered visual element.

Do not recreate the mock iOS status bar from Figma.

## Accessibility

Do not blindly reproduce very small text from the wireframe.

Prioritize readable typography, adequate contrast, accessible touch targets, and semantic interaction while preserving the visual identity.

## Assets

Figma MCP asset URLs are temporary.

Any asset required by committed application code must be stored locally in the repository.

Do not recreate existing visual assets approximately when the original asset is available.

## Scope Discipline

Implement only the current cycle.

Do not anticipate future screens, integrations, authentication, native USB, backend, or infrastructure unless explicitly requested.

Do not refactor unrelated code without a concrete reason.

## Validation

Before completing a development cycle, run the relevant checks, normally including:

- `npm run lint`
- `npm run typecheck`
- `npm run format:check`
- `npx expo install --check`

Use `expo-doctor` when dependencies, Expo configuration, or native compatibility are affected.

Fix regressions introduced by the current work.

## Git

Do not commit or push unless explicitly requested.

## Completion Report

At the end of each cycle, report:

- what changed
- important architectural decisions
- files created/changed
- validation results
- real unresolved issues

Do not list intentionally deferred future-cycle work as a defect.
