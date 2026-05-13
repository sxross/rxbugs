import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/bugs': 'http://localhost:5000',
      '/auth': 'http://localhost:5000',
      '/agents': 'http://localhost:5000',
      '/api': 'http://localhost:5000',
    },
  },
})
