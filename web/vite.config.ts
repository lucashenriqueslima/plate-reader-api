import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Forward API calls to the local FastAPI server, so no CORS setup is needed.
    proxy: { '/v1': 'http://localhost:8000' },
  },
})
