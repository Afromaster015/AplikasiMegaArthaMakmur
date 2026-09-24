import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: { target: ['chrome109', 'edge109'], sourcemap: false, cssCodeSplit: true },
  server: { proxy: { '/api': 'http://127.0.0.1:8765' } },
  test: { environment: 'jsdom', globals: true }
})
