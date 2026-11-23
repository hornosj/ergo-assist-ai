import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// O /api vai para o Django: mesma origem no navegador, sem CORS no dev.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://localhost:8000', '/admin': 'http://localhost:8000' },
  },
})
