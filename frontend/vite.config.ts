import path from 'path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const backendUrl = process.env.BACKEND_PROXY_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/health': { target: backendUrl, changeOrigin: true },
      '/api': {
        target: backendUrl,
        changeOrigin: true
      }
    }
  }
})
