import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API_TARGET = process.env.VITE_API_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: [
      'leaflet',
      'react-leaflet',
      '@tanstack/react-query',
      'zustand',
      'react-router-dom',
      'react-hot-toast',
    ],
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/auth':          API_TARGET,
      '/users':         API_TARGET,
      '/listings':      API_TARGET,
      '/fraud':         API_TARGET,
      '/contracts':     API_TARGET,
      '/agent':         API_TARGET,
      '/areas':         API_TARGET,
      '/estimator':     API_TARGET,
      '/notifications': API_TARGET,
      '/roommate':      API_TARGET,
      '/health':        API_TARGET,
    },
  },
})
