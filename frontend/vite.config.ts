import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/',
  build: {
    outDir: '../docs',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          // Split heavy chart library
          if (id.includes('node_modules/recharts')) return 'vendor-recharts'
          // FontAwesome core
          if (id.includes('@fortawesome')) return 'vendor-icons'
          // Animation lib
          if (id.includes('node_modules/framer-motion')) return 'vendor-motion'
        },
      },
    },
  },
})
