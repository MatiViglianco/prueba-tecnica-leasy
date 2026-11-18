import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// In development the dev server proxies /api to Django, mirroring what nginx
// does in the Docker image. The browser always talks to a single origin, so
// the backend needs no CORS configuration.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.API_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': { target: apiProxyTarget, changeOrigin: true },
      },
    },
  }
})
