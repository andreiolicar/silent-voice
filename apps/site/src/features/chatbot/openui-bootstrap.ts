// @openuidev/react-lang 1.0.1 auto-mounts its development inspector unless this
// sentinel is already set. Keep product pages free of inspector UI/CDN loads.
// Recheck this package-specific guard when upgrading OpenUI.
const runtime = globalThis as typeof globalThis & { [key: symbol]: unknown }
runtime[Symbol.for('openui.devtools.autoMount')] = true
