import { createRequire } from 'node:module'
import { dirname } from 'node:path'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
const require = createRequire(import.meta.url)
const webReact = dirname(require.resolve('react/package.json'))
const webDom = dirname(require.resolve('react-dom/package.json'))
export default defineConfig({
  plugins:[react()],
  resolve:{alias:[{find:/^react(?=\/|$)/,replacement:webReact},{find:/^react-dom(?=\/|$)/,replacement:webDom}],dedupe:['react','react-dom','motion','motion-dom','motion-utils']},
  test:{environment:'jsdom',include:['src/**/*.test.ts','src/**/*.test.tsx'],setupFiles:['./scripts/test-setup.ts'],clearMocks:true,deps:{optimizer:{client:{enabled:true,include:['react','react-dom/client','react-dom/test-utils','@testing-library/react','lucide-react','react-router-dom','motion/react','motion/react-m']}}},server:{deps:{inline:['@openuidev/react-lang','@openuidev/react-ui','react','react-dom','motion','framer-motion','react-router','@nanostores/react']}}},
})
