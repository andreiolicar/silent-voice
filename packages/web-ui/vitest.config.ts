import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
export default defineConfig({plugins:[react()],resolve:{dedupe:['react','react-dom']},test:{environment:'jsdom',include:['src/**/*.test.tsx'],setupFiles:['./test/setup.ts']}})
