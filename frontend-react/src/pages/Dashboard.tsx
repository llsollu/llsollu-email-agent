import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, Clock, Cpu, Inbox, Send } from 'lucide-react'
import { api } from '@/lib/api'
import type { AnalysisStats, DashboardData, SchedulerStats } from '@/lib/types'
import { useAgents } from '@/hooks/useAgents'
import { issueLabelMap, type IssueType } from '@/lib/issueTypes'
import { cn } from '@/lib/utils'

const PALETTE = ['#14b8a6', '#0ea5e9', '#f59e0b', '#8b5cf6', '#ff6b57', '#22c55e', '#e11d48', '#64748b']

function fmtKst(iso?: string | null) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (isNaN(+d)) return '-'
  const k = new Date(d.getTime() + 9 * 3600 * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(k.getUTCMonth() + 1)}/${p(k.getUTCDate())} ${p(k.getUTCHours())}:${p(k.getUTCMinutes())}`
}

export function Dashboard() {
  const agents = useAgents()
  const q = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.dashboard,
    // 응답이 집계(수 KB)라 폴링해도 가벼움 → 새 메일 처리 시 자동 반영(60초).
    refetchInterval: 60_000,
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  })

  const trackerConfig = agents.data?.find((a) => a.template_key === 'project_tracker')?.config
  const issueLabels = useMemo(
    () => issueLabelMap(trackerConfig?.issue_types as IssueType[] | undefined),
    [trackerConfig],
  )

  const d = q.data
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-[880px] p-7">
        <div className="mb-5 flex items-baseline justify-between">
          <h1 className="text-2xl font-extrabold tracking-tight">대시보드</h1>
          <span className="text-xs font-medium text-muted">45초마다 자동 갱신</span>
        </div>

        {q.isLoading && <p className="text-sm text-muted">불러오는 중…</p>}
        {q.isError && <p className="text-sm font-semibold text-cancelled">대시보드를 불러오지 못했습니다</p>}

        {d && (
          <div className="space-y-6">
            <AgentStatus agents={d.agents} />
            {d.analysis && <AnalysisSection s={d.analysis} issueLabels={issueLabels} />}
            {d.scheduler && <SchedulerSection s={d.scheduler} />}
          </div>
        )}
      </div>
    </div>
  )
}

/* ─────────── 에이전트 상태 ─────────── */
function AgentStatus({ agents }: { agents: DashboardData['agents'] }) {
  const navigate = useNavigate()
  const dot = (s: string) => (s === 'active' ? 'bg-active' : s === 'error' ? 'bg-cancelled' : 'bg-onhold')
  const label = (s: string) => (s === 'active' ? '정상' : s === 'error' ? '오류' : s === 'configuring' ? '설정 중' : s)
  return (
    <Card title="에이전트 상태">
      <div className="flex flex-wrap gap-2">
        {agents.map((a) => (
          <button key={a.id} onClick={() => navigate(`/agents/${a.id}`)}
            className="flex items-center gap-2 rounded-xl border border-line bg-bg px-3 py-2 text-sm hover:border-primary">
            <span className={cn('h-2 w-2 rounded-full', dot(a.status))} />
            <span className="font-bold">{a.name}</span>
            <span className="text-xs font-medium text-muted">{label(a.status)}</span>
          </button>
        ))}
      </div>
    </Card>
  )
}

/* ─────────── 분석 섹션 ─────────── */
function AnalysisSection({ s, issueLabels }: { s: AnalysisStats; issueLabels: Record<string, string> }) {
  const k = s.kpis
  const deltaPct = k.week_prev > 0 ? Math.round(((k.week_analyzed - k.week_prev) / k.week_prev) * 100) : null
  return (
    <section className="space-y-4">
      <SectionTitle icon={<Inbox size={16} />} text="메일 분석" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi value={k.week_analyzed} label="이번 주 분석"
          sub={deltaPct === null ? '지난주 없음' : `${deltaPct >= 0 ? '▲' : '▼'} ${Math.abs(deltaPct)}% vs 지난주`}
          subColor={deltaPct === null ? 'muted' : deltaPct >= 0 ? 'active' : 'cancelled'} />
        <Kpi value={k.open_issues} label="미해결 이슈" danger
          sub={`스토리보드 ${k.statuses.storyboard ?? 0} · 진행 ${k.statuses.active ?? 0} · 보류 ${k.statuses.on_hold ?? 0}`} />
        <Kpi value={k.active_cards} label="진행 중 카드"
          sub={`진행 ${k.statuses.active ?? 0} · 보류 ${k.statuses.on_hold ?? 0}`} />
        <Kpi value={`${k.direct_ratio}%`} label="직접수신 비율"
          sub={`참조 ${pct(s.receipt.cc, s.receipt)}% · 기타 ${pct(s.receipt.other, s.receipt)}%`} />
      </div>

      <Card title="분석량 추이 · 최근 30일 (일별)">
        {s.daily.length === 0 ? <Empty /> : <VBars data={s.daily} />}
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="고객사 Top · 최근 90일">
          {s.clients.length === 0 ? <Empty /> : <HBars items={s.clients.map((c) => ({ name: c.name, count: c.count }))} />}
        </Card>
        <Card title="자동 태그 분포 · 최근 30일">
          {s.categories.length === 0 ? <Empty /> : (
            <Donut slices={s.categories.slice(0, 6).map((c, i) => ({ label: c.name, value: c.count, color: PALETTE[i % PALETTE.length] }))} />
          )}
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="이슈 유형 · 미해결">
          {s.issue_types.length === 0 ? <Empty text="미해결 이슈 없음" /> : (
            <HBars items={s.issue_types.map((t) => ({ name: issueLabels[t.type] ?? t.type, count: t.count }))} />
          )}
        </Card>
        <Card title="수신 역할 · 최근 30일 · LLM 사용량">
          <Donut slices={[
            { label: '직접수신', value: s.receipt.to, color: '#0ea5e9' },
            { label: '참조', value: s.receipt.cc, color: '#8b5cf6' },
            { label: '기타', value: s.receipt.other, color: '#64748b' },
          ]} />
          <div className="mt-3 flex items-center gap-2 border-t border-line pt-3 text-[13px] text-muted">
            <Cpu size={15} />
            이번 달 <b className="text-ink">{(s.llm.tokens_in + s.llm.tokens_out).toLocaleString()}</b> 토큰 · 분석 {s.llm.count.toLocaleString()}건
          </div>
        </Card>
      </div>
    </section>
  )
}

/* ─────────── 스케줄러 섹션 ─────────── */
function SchedulerSection({ s }: { s: SchedulerStats }) {
  const k = s.kpis
  const total = k.week_sent + k.week_failed
  const failRate = total > 0 ? Math.round((k.week_failed / total) * 100) : 0
  return (
    <section className="space-y-4">
      <SectionTitle icon={<Send size={16} />} text="메일 자동 발송" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi value={k.week_sent} label="이번 주 발송" />
        <Kpi value={k.week_failed} label="이번 주 실패" danger={k.week_failed > 0} sub={`실패율 ${failRate}%`} />
        <Kpi value={`${k.active_schedules}/${k.total_schedulers}`} label="활성 스케줄" />
        <Kpi value={fmtKst(k.next_run_at)} label="다음 발송" small />
      </div>

      <Card title="발송량 추이 · 최근 30일 (성공/실패)">
        {s.daily.length === 0 ? <Empty /> : <VBarsStacked data={s.daily} />}
      </Card>

      {s.agents.length > 1 && (
        <Card title="스케줄러별">
          <div className="space-y-1.5">
            {s.agents.map((a) => (
              <div key={a.id} className="flex items-center gap-3 rounded-lg border border-line bg-bg px-3 py-2 text-sm">
                <span className={cn('h-2 w-2 rounded-full', a.enabled ? 'bg-active' : 'bg-muted')} />
                <span className="flex-1 truncate font-bold">{a.name}</span>
                <span className="text-xs font-medium text-muted">주간 {a.week_sent}건{a.week_failed ? ` · 실패 ${a.week_failed}` : ''}</span>
                <span className="text-xs font-medium text-muted">다음 {fmtKst(a.next_run_at)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title="최근 발송">
        {s.recent.length === 0 ? <Empty text="발송 이력 없음" /> : (
          <div className="space-y-1">
            {s.recent.map((r, i) => (
              <div key={i} className="flex items-center gap-2 py-1 text-[13px]">
                {r.status === 'sent' ? <CheckCircle2 size={14} className="shrink-0 text-active" />
                  : r.status === 'failed' ? <AlertTriangle size={14} className="shrink-0 text-cancelled" />
                  : <Clock size={14} className="shrink-0 text-muted" />}
                <span className="truncate">{r.subject}</span>
                <span className="ml-auto shrink-0 text-xs text-muted">{r.agent} · {fmtKst(r.sent_at)}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </section>
  )
}

/* ─────────── 공통 UI ─────────── */
function pct(v: number, r: { to: number; cc: number; other: number }) {
  const t = r.to + r.cc + r.other || 1
  return Math.round((v / t) * 100)
}
function SectionTitle({ icon, text }: { icon: React.ReactNode; text: string }) {
  return <div className="flex items-center gap-2 text-[15px] font-extrabold"><span className="text-primary">{icon}</span>{text}</div>
}
function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className="mb-3 text-[13px] font-bold text-muted">{title}</div>
      {children}
    </div>
  )
}
function Kpi({ value, label, sub, subColor = 'muted', danger, small }: {
  value: React.ReactNode; label: string; sub?: string; subColor?: 'muted' | 'active' | 'cancelled'; danger?: boolean; small?: boolean
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className={cn('font-extrabold', small ? 'text-lg' : 'text-2xl', danger ? 'text-cancelled' : 'text-primary')}>{value}</div>
      <div className="mt-0.5 text-[13px] font-semibold text-muted">{label}</div>
      {sub && <div className={cn('mt-1 text-[11px] font-bold',
        subColor === 'active' ? 'text-active' : subColor === 'cancelled' ? 'text-cancelled' : 'text-muted')}>{sub}</div>}
    </div>
  )
}
function Empty({ text = '데이터 없음' }: { text?: string }) {
  return <div className="py-6 text-center text-[13px] font-medium text-muted">{text}</div>
}

/* ─────────── 인라인 SVG 차트 ─────────── */
function VBars({ data }: { data: { date: string; count: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.count))
  const n = data.length, W = 620, H = 96, gap = 3
  const bw = (W - gap * (n - 1)) / n
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none" role="img" aria-label="일별 분석량">
      {data.map((d, i) => {
        const h = Math.max(2, Math.round((d.count / max) * (H - 4)))
        return <rect key={d.date} x={i * (bw + gap)} y={H - h} width={bw} height={h} rx={2} fill="#14b8a6"><title>{d.date}: {d.count}</title></rect>
      })}
    </svg>
  )
}
function VBarsStacked({ data }: { data: { date: string; sent: number; failed: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.sent + d.failed))
  const n = data.length, W = 620, H = 96, gap = 3
  const bw = (W - gap * (n - 1)) / n
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none" role="img" aria-label="일별 발송량">
      {data.map((d, i) => {
        const sh = Math.round((d.sent / max) * (H - 4))
        const fh = Math.round((d.failed / max) * (H - 4))
        const x = i * (bw + gap)
        return (
          <g key={d.date}>
            {d.failed > 0 && <rect x={x} y={H - sh - fh} width={bw} height={fh} rx={1} fill="#f43f5e"><title>{d.date} 실패 {d.failed}</title></rect>}
            {d.sent > 0 && <rect x={x} y={H - sh} width={bw} height={sh} rx={1} fill="#22c55e"><title>{d.date} 성공 {d.sent}</title></rect>}
          </g>
        )
      })}
    </svg>
  )
}
function HBars({ items }: { items: { name: string; count: number }[] }) {
  const max = Math.max(1, ...items.map((i) => i.count))
  return (
    <div className="space-y-1.5">
      {items.map((it, i) => (
        <div key={it.name + i} className="flex items-center gap-2 text-[13px]">
          <span className="w-24 shrink-0 truncate text-muted" title={it.name}>{it.name}</span>
          <span className="h-2 flex-1 overflow-hidden rounded-full bg-line/60">
            <span className="block h-full rounded-full" style={{ width: `${(it.count / max) * 100}%`, background: PALETTE[i % PALETTE.length] }} />
          </span>
          <span className="w-8 text-right tabular-nums text-muted">{it.count}</span>
        </div>
      ))}
    </div>
  )
}
function Donut({ slices }: { slices: { label: string; value: number; color: string }[] }) {
  const total = slices.reduce((s, x) => s + x.value, 0) || 1
  let before = 0
  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 42 42" width="88" height="88" role="img" aria-label="분포">
        <circle cx="21" cy="21" r="15.915" fill="none" stroke="var(--line)" strokeWidth="9" />
        {slices.filter((s) => s.value > 0).map((s) => {
          const p = (s.value / total) * 100
          const el = (
            <circle key={s.label} cx="21" cy="21" r="15.915" fill="none" stroke={s.color} strokeWidth="9"
              strokeDasharray={`${p} ${100 - p}`} strokeDashoffset={25 - before} />
          )
          before += p
          return el
        })}
      </svg>
      <div className="space-y-1 text-[13px]">
        {slices.map((s) => (
          <div key={s.label} className="flex items-center gap-1.5 text-muted">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />
            {s.label} {Math.round((s.value / total) * 100)}%
          </div>
        ))}
      </div>
    </div>
  )
}
