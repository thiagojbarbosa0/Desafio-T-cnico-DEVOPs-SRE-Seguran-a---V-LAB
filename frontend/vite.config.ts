import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Development proxy only. Configure Firebase emulator separately for offline auth.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/users': 'http://127.0.0.1:5000',
      '/chats': 'http://127.0.0.1:5000',
      '/hash': 'http://127.0.0.1:5000',
    },
  },
})
