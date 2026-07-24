import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { LogOut, Plus } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/store/auth'
import { useAgents } from '@/hooks/useAgents'
import { ThemeToggle } from '@/components/ThemeToggle'
import { cn } from '@/lib/utils'

export function AppShell() {
  const { user, setUser } = useAuth()
  const agents = useAgents()
  const navigate = useNavigate()

  async function logout() {
    await api.logout().catch(() => {})
    setUser(null)
    navigate('/')
  }

  return (
    <div className="flex h-full">
      <aside className="flex w-72 flex-col border-r border-line bg-surface">
        <div className="flex items-center gap-3 px-5 pb-4 pt-6">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-primary to-brand2 text-lg font-black text-white">
            L
          </div>
          <div className="min-w-0">
            <div className="text-base font-extrabold">Email Agent</div>
            <div className="truncate text-[13px] font-medium text-muted">{user?.email}</div>
          </div>
        </div>

        <div className="px-5 pb-2 pt-1 text-[13px] font-bold uppercase tracking-wide text-muted">내 에이전트</div>
        <nav className="flex-1 overflow-y-auto px-3">
          {agents.isLoading && <p className="px-3 py-2 text-sm text-muted">불러오는 중…</p>}
          {agents.data?.length === 0 && <p className="px-3 py-2 text-sm text-muted">아직 에이전트가 없어요</p>}
          {agents.data?.map((a) => (
            <NavLink
              key={a.id}
              to={`/agents/${a.id}`}
              className={({ isActive }) =>
                cn(
                  'mb-1 flex items-center gap-3 rounded-xl px-2.5 py-2.5 transition',
                  isActive ? 'bg-primary/10' : 'hover:bg-line/50',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={cn(
                      'grid h-9 w-9 shrink-0 place-items-center rounded-[10px] text-sm font-black',
                      isActive ? 'bg-primary text-white' : 'bg-primary/10 text-primary',
                    )}
                  >
                    {a.view_type === 'kanban' ? '분' : '발'}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate font-bold">{a.name}</span>
                    <span className="block text-[13px] font-medium text-muted">{statusLabel(a.status)}</span>
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-line p-3">
          <button
            onClick={() => navigate('/add')}
            className="mb-1 flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-2.5 font-bold text-white transition hover:bg-primary-hover"
          >
            <Plus size={18} /> 에이전트 추가
          </button>
          <div className="flex items-center justify-between">
            <ThemeToggle />
            <button onClick={logout} className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-muted hover:bg-line/50">
              <LogOut size={16} /> 로그아웃
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden bg-bg">
        <Outlet />
      </main>
    </div>
  )
}

function statusLabel(s: string): string {
  const map: Record<string, string> = { configuring: '구성 중…', active: '실행 중', paused: '일시정지', error: '오류' }
  return map[s] ?? s
}
