import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dashboard calls /api/* which Vite proxies to FastAPI on 127.0.0.1:8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false } },
  },
})
