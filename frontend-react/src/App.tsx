import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/store/auth'
import { Login } from '@/pages/Login'
import { AppShell } from '@/layout/AppShell'
import { AgentView } from '@/pages/AgentView'

function App() {
  const { user, setUser } = useAuth()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [setUser])

  if (loading) {
    return (
      <div className="grid h-full place-items-center bg-bg text-muted">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-primary" />
      </div>
    )
  }

  if (!user) return <Login />

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<EmptyState />} />
        <Route path="agents/:id" element={<AgentView />} />
        <Route path="add" element={<AddPlaceholder />} />
        <Route path="*" element={<EmptyState />} />
      </Route>
    </Routes>
  )
}

function EmptyState() {
  return (
    <div className="grid h-full place-items-center">
      <div className="text-center">
        <div className="mx-auto mb-4 grid h-[72px] w-[72px] place-items-center rounded-2xl bg-primary/10 text-3xl text-primary">✦</div>
        <p className="text-base font-bold">에이전트를 선택하거나 추가하세요</p>
        <p className="mt-1 text-sm font-medium text-muted">좌측 목록에서 시작할 수 있어요</p>
      </div>
    </div>
  )
}

function AddPlaceholder() {
  return (
    <div className="grid h-full place-items-center">
      <p className="text-sm font-medium text-muted">에이전트 추가 마법사는 Phase 3에서 구현됩니다.</p>
    </div>
  )
}

export default App
