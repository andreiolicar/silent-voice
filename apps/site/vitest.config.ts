import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    setupFiles: ['./scripts/test-setup.ts'],
    clearMocks: true,
    server: { deps: { inline: ['@openuidev/react-ui'] } },
  },
})
