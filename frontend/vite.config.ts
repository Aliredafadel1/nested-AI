import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/listings': 'http://localhost:8000',
      '/fraud': 'http://localhost:8000',
      '/contracts': 'http://localhost:8000',
      '/agent': 'http://localhost:8000',
      '/areas': 'http://localhost:8000',
      '/estimator': 'http://localhost:8000',
      '/notifications': 'http://localhost:8000',
      '/roommate': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
