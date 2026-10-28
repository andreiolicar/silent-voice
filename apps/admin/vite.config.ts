import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { privateFiles } from '../../infra/vite-private.ts'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  return {
    base: '/admin/',
    plugins: [react(), tailwindcss()],
    resolve: { dedupe: ['react','react-dom','motion','motion-dom','motion-utils'] },
    server: { proxy: { '/api': env.VITE_API_PROXY || 'http://127.0.0.1:3001' }, fs: { deny: privateFiles } },
  }
})
