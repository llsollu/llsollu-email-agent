import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { ApiError, bootAuth } from '@/lib/api'
import { useAuth } from '@/store/auth'

bootAuth() // 데스크톱: 저장된 Bearer 토큰 복원 후 렌더

const queryClient = new QueryClient({
  // 세션 만료(401) 시 자동 로그아웃 → 로그인 화면으로.
  queryCache: new QueryCache({
    onError: (err) => {
      if (err instanceof ApiError && err.status === 401) useAuth.getState().setUser(null)
    },
  }),
  defaultOptions: {
    queries: { retry: (count, err) => !(err instanceof ApiError && err.status === 401) && count < 1, refetchOnWindowFocus: false },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
