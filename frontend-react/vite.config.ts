import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// 개발 서버는 /api 를 백엔드(FastAPI)로 프록시 → 브라우저 관점 동일 오리진(쿠키 유지).
// 프로덕션 웹 빌드는 FastAPI 가 dist/ 를 동일 오리진으로 서빙하므로 프록시 불필요.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
