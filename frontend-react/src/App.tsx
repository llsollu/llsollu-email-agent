import { useQuery } from '@tanstack/react-query'
import { cn } from '@/lib/utils'

type Health = { status: string; templates: string[] }

function useHealth() {
  return useQuery<Health>({
    queryKey: ['health'],
    queryFn: async () => {
      const r = await fetch('/api/health', { credentials: 'include' })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      return r.json()
    },
  })
}

const STATUS = [
  ['스토리보드', 'bg-storyboard/15 text-storyboard'],
  ['진행 중', 'bg-active/15 text-active'],
  ['보류', 'bg-onhold/15 text-onhold'],
  ['완료', 'bg-completed/15 text-completed'],
  ['취소', 'bg-cancelled/15 text-cancelled'],
] as const

function App() {
  const health = useHealth()

  return (
    <div className="min-h-full">
      {/* 브랜드 헤더 */}
      <header className="flex items-center gap-3 px-8 py-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-[#9b5cf6] text-lg font-black text-white shadow-lg shadow-primary/30">
          L
        </div>
        <div>
          <h1 className="text-xl font-extrabold tracking-tight">LLSOLLU Email Agent</h1>
          <p className="text-sm font-medium text-muted">React + Tauri 리뉴얼 · Phase 0 미리보기</p>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-8 pb-16">
        {/* 백엔드 연결 확인 */}
        <section className="rounded-2xl border border-line bg-surface p-6 shadow-sm">
          <div className="text-sm font-bold text-muted">백엔드 연결 상태</div>
          <div className="mt-3 text-lg font-semibold">
            {health.isLoading && '확인 중…'}
            {health.isError && <span className="text-cancelled">연결 실패 (백엔드 실행 확인)</span>}
            {health.data && (
              <span className="text-active">
                정상 · 템플릿 {health.data.templates.length}종 ({health.data.templates.join(', ')})
              </span>
            )}
          </div>
        </section>

        {/* 테마 시안 */}
        <h2 className="mt-10 mb-4 text-lg font-extrabold tracking-tight">테마 시안</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Card title="버튼">
            <div className="flex flex-wrap gap-3">
              <button className="rounded-xl bg-primary px-5 py-2.5 font-bold text-white transition hover:bg-primary-hover">
                기본
              </button>
              <button className="rounded-xl bg-accent px-5 py-2.5 font-bold text-white transition hover:brightness-95">
                강조
              </button>
              <button className="rounded-xl border border-line bg-surface px-5 py-2.5 font-bold text-ink transition hover:bg-line/40">
                아웃라인
              </button>
            </div>
          </Card>
          <Card title="상태 배지">
            <div className="flex flex-wrap gap-2">
              {STATUS.map(([label, cls]) => (
                <span key={label} className={cn('rounded-full px-3 py-1 text-xs font-semibold', cls)}>
                  {label}
                </span>
              ))}
            </div>
          </Card>
          <Card title="입력">
            <input
              placeholder="검색…"
              className="w-full rounded-xl border border-line bg-surface px-4 py-2.5 outline-none focus:border-primary"
            />
          </Card>
          <Card title="샘플 카드">
            <p className="font-semibold">이씨에스텔레콤</p>
            <p className="text-sm font-medium text-muted">KB카드 생성형 콜봇 STT 대응 개발</p>
            <div className="mt-2 flex gap-2">
              <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">제안</span>
              <span className="rounded-full bg-active/15 px-2.5 py-1 text-xs font-semibold text-active">진행 중</span>
            </div>
          </Card>
        </div>
      </main>
    </div>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5 shadow-sm">
      <div className="mb-3 text-sm font-bold text-muted">{title}</div>
      {children}
    </div>
  )
}

export default App
