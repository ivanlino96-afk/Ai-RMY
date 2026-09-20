import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev server proxies /api (including the WS event stream and MJPEG video
// stream) to the FastAPI backend, which in production serves this app's
// build directly — see app/backend/main.py.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        ws: true,
      },
    },
  },
})
