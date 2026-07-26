import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Cpu, Database, Server, Users } from 'lucide-react'
import { api } from '@/lib/api'
import type { AdminAgent, AdminCapacity, AdminOps, AdminUsage, AdminUser } from '@/lib/types'
import { cn } from '@/lib/utils'

type Tab = 'users' | 'agents' | 'usage' | 'ops' | 'capacity'
const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: 'users', label: '사용자', icon: <Users size={15} /> },
  { key: 'agents', label: '에이전트 현황', icon: <Server size={15} /> },
  { key: 'usage', label: 'LLM 사용량', icon: <Cpu size={15} /> },
  { key: 'ops', label: '운영 상태', icon: <AlertTriangle size={15} /> },
  { key: 'capacity', label: '데이터·용량', icon: <Database size={15} /> },
]

function fmtKst(iso?: string | null) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (isNaN(+d)) return '-'
  const k = new Date(d.getTime() + 9 * 3600 * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${k.getUTCFullYear()}-${p(k.getUTCMonth() + 1)}-${p(k.getUTCDate())} ${p(k.getUTCHours())}:${p(k.getUTCMinutes())}`
}
function bytes(n: number) {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)} GB`
  if (n >= 1e6) return `${(n / 1e6).toFixed(0)} MB`
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)} KB`
  return `${n} B`
}
function tokens(n: number) {
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`
  return String(n)
}

export function Admin() {
  const [tab, setTab] = useState<Tab>('users')
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-[900px] p-7">
        <h1 className="mb-4 text-2xl font-extrabold tracking-tight">관리자</h1>
        <div className="mb-5 flex gap-1 border-b border-line">
          {TABS.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={cn('-mb-px flex items-center gap-1.5 border-b-2 px-3.5 py-2 text-sm font-bold transition',
                tab === t.key ? 'border-primary text-primary' : 'border-transparent text-muted hover:text-ink')}>
              {t.icon}{t.label}
            </button>
          ))}
        </div>
        {tab === 'users' && <UsersTab />}
        {tab === 'agents' && <AgentsTab />}
        {tab === 'usage' && <UsageTab />}
        {tab === 'ops' && <OpsTab />}
        {tab === 'capacity' && <CapacityTab />}
      </div>
    </div>
  )
}

/* ─────────── 사용자 ─────────── */
function UsersTab() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin', 'users'], queryFn: api.adminUsers })
  const m = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, boolean> }) => api.adminPatchUser(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
  if (q.isLoading) return <Loading />
  if (q.isError) return <Err />
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-surface">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs font-bold text-muted">
            <Th>사용자</Th><Th>부서</Th><Th>에이전트</Th><Th>마지막 로그인</Th><Th>권한</Th><Th>상태</Th><Th>작업</Th>
          </tr>
        </thead>
        <tbody>
          {q.data!.map((u: AdminUser) => (
            <tr key={u.id} className="border-b border-line last:border-0">
              <Td><div className="font-bold">{u.display_name || u.email.split('@')[0]}</div><div className="text-xs text-muted">{u.email}</div></Td>
              <Td className="text-muted">{u.department || '-'}</Td>
              <Td>{u.agent_count}</Td>
              <Td className="text-muted">{fmtKst(u.last_login_at)}</Td>
              <Td>
                <Pill on={u.is_admin} className={u.is_admin ? 'bg-brand2/15 text-brand2' : 'bg-line text-muted'}>
                  {u.is_admin ? '관리자' : '일반'}{u.bootstrap ? '(고정)' : ''}
                </Pill>
              </Td>
              <Td>
                <Pill className={u.is_active ? 'bg-active/15 text-active' : 'bg-onhold/15 text-onhold'}>
                  {u.is_active ? '활성' : '비활성'}
                </Pill>
              </Td>
              <Td>
                <div className="flex flex-wrap gap-1.5">
                  {!u.bootstrap && (
                    <Act onClick={() => m.mutate({ id: u.id, body: { is_admin: !u.is_admin } })}>
                      {u.is_admin ? '관리자 해제' : '관리자 지정'}
                    </Act>
                  )}
                  {!u.bootstrap && (
                    <Act onClick={() => m.mutate({ id: u.id, body: { is_active: !u.is_active } })}>
                      {u.is_active ? '비활성화' : '활성화'}
                    </Act>
                  )}
                  {u.has_password && (
                    <Act onClick={() => { if (confirm(`${u.email}의 비밀번호를 초기화할까요? 다음 로그인 시 재설정합니다.`)) m.mutate({ id: u.id, body: { reset_password: true } }) }}>
                      비번 초기화
                    </Act>
                  )}
                </div>
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ─────────── 에이전트 현황 ─────────── */
function AgentsTab() {
  const q = useQuery({ queryKey: ['admin', 'agents'], queryFn: api.adminAgents, refetchInterval: 60_000 })
  if (q.isLoading) return <Loading />
  if (q.isError) return <Err />
  const agents = q.data!
  const errored = agents.filter((a) => a.status === 'error')
  return (
    <div className="space-y-4">
      {errored.length > 0 && (
        <Card className="border-cancelled/40">
          <div className="mb-2 text-[13px] font-bold text-cancelled">⚠ 조치 필요 · 오류 {errored.length}</div>
          {errored.map((a) => (
            <div key={a.id} className="border-t border-line py-2 first:border-0">
              <div className="flex items-center gap-2 text-sm"><span className="font-bold">{a.name}</span><span className="text-xs text-muted">{a.owner}</span></div>
              <div className="text-xs font-medium text-cancelled">{a.error_detail || '오류'}</div>
            </div>
          ))}
        </Card>
      )}
      <div className="overflow-x-auto rounded-2xl border border-line bg-surface">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-line text-left text-xs font-bold text-muted">
            <Th>에이전트</Th><Th>소유자</Th><Th>종류</Th><Th>상태</Th><Th>마지막 실행</Th>
          </tr></thead>
          <tbody>
            {agents.map((a: AdminAgent) => (
              <tr key={a.id} className="border-b border-line last:border-0">
                <Td className="font-bold">{a.name}</Td>
                <Td className="text-muted">{a.owner}</Td>
                <Td className="text-muted">{a.template_key === 'project_tracker' ? '분석' : '발송'}</Td>
                <Td><Pill className={statusCls(a.status)}>{statusLabel(a.status)}</Pill></Td>
                <Td className="text-muted">{fmtKst(a.last_run_at)} {a.last_run_status ? `· ${a.last_run_status}` : ''}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ─────────── LLM 사용량 ─────────── */
function UsageTab() {
  const q = useQuery({ queryKey: ['admin', 'usage'], queryFn: api.adminUsage })
  if (q.isLoading) return <Loading />
  if (q.isError) return <Err />
  const u = q.data as AdminUsage
  const maxUser = Math.max(1, ...u.by_user.map((x) => x.tokens))
  const maxMonth = Math.max(1, ...u.monthly.map((x) => x.tokens))
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <Kpi value={tokens(u.month_total_tokens)} label="이번 달 총 토큰" />
        <Kpi value={u.month_total_count.toLocaleString()} label="이번 달 분석 건수" />
      </div>
      <Card>
        <H>월별 토큰 · 최근 6개월</H>
        <div className="flex items-end gap-3" style={{ height: 110 }}>
          {u.monthly.map((mo) => (
            <div key={mo.month} className="flex flex-1 flex-col items-center gap-1">
              <div className="w-full rounded-t bg-primary" style={{ height: `${(mo.tokens / maxMonth) * 84}px` }} title={`${mo.tokens.toLocaleString()} 토큰`} />
              <span className="text-[11px] text-muted">{mo.month.slice(2, 7)}</span>
            </div>
          ))}
          {u.monthly.length === 0 && <Empty />}
        </div>
      </Card>
      <Card>
        <H>이번 달 사용자별 토큰 (Top 10)</H>
        {u.by_user.length === 0 ? <Empty /> : u.by_user.map((x, i) => (
          <div key={x.name + i} className="flex items-center gap-2 py-1 text-[13px]">
            <span className="w-24 shrink-0 truncate text-muted">{x.name}</span>
            <span className="h-2 flex-1 overflow-hidden rounded-full bg-line/60"><span className="block h-full rounded-full bg-primary" style={{ width: `${(x.tokens / maxUser) * 100}%` }} /></span>
            <span className="w-14 text-right tabular-nums text-muted">{tokens(x.tokens)}</span>
          </div>
        ))}
        <div className="mt-2 text-[11px] text-muted">자가호스팅 모델이라 비용은 0 — 토큰량은 부하 지표입니다.</div>
      </Card>
    </div>
  )
}

/* ─────────── 운영 상태 ─────────── */
function OpsTab() {
  const q = useQuery({ queryKey: ['admin', 'ops'], queryFn: api.adminOps, refetchInterval: 30_000 })
  if (q.isLoading) return <Loading />
  if (q.isError) return <Err />
  const o = q.data as AdminOps
  const modeLabel = o.collect_mode === 'polling' ? '폴링' : o.collect_mode === 'webhook' ? 'Webhook' : '비활성'
  const hbFresh = o.worker_heartbeat && (Date.now() - new Date(o.worker_heartbeat).getTime() < 180_000)
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-4">
        <Kpi value={modeLabel} label="수집 모드" small />
        <Kpi value={hbFresh ? '정상' : '점검'} label="워커 하트비트" small danger={!hbFresh} />
        <Kpi value={o.queued ?? '-'} label="대기 큐" />
        <Kpi value={o.failed_24h} label="24h 실패 실행" danger={o.failed_24h > 0} />
      </div>
      <Card>
        <H>최근 실패 실행</H>
        {o.recent_failures.length === 0 ? <Empty text="최근 실패 없음" /> : o.recent_failures.map((f, i) => (
          <div key={i} className="border-t border-line py-2 text-[13px] first:border-0">
            <div className="flex items-center gap-2"><span className="font-bold">{f.agent}</span><span className="text-xs text-muted">{f.trigger} · {fmtKst(f.at)}</span></div>
            <div className="text-xs font-medium text-cancelled">{f.error}</div>
          </div>
        ))}
      </Card>
      <div className="text-[11px] text-muted">하트비트는 워커 cron(매분) 기준. 3분 이상 갱신 없으면 '점검'.</div>
    </div>
  )
}

/* ─────────── 데이터·용량 ─────────── */
function CapacityTab() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin', 'capacity'], queryFn: api.adminCapacity })
  const [msg, setMsg] = useState<string | null>(null)
  const prune = useMutation({ mutationFn: api.adminPruneRuns, onSuccess: (r) => { setMsg(`실행 이력 ${r.deleted}건 정리 완료`); qc.invalidateQueries({ queryKey: ['admin', 'capacity'] }) } })
  const archive = useMutation({ mutationFn: api.adminArchiveProjects, onSuccess: (r) => { setMsg(`카드 ${r.archived}건 아카이브 완료`); qc.invalidateQueries({ queryKey: ['admin', 'capacity'] }) } })
  if (q.isLoading) return <Loading />
  if (q.isError) return <Err />
  const c = q.data as AdminCapacity
  return (
    <div className="space-y-4">
      <Kpi value={bytes(c.db_bytes)} label="전체 DB 크기" />
      <div className="overflow-x-auto rounded-2xl border border-line bg-surface">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-line text-left text-xs font-bold text-muted"><Th>테이블</Th><Th>행 수(추정)</Th><Th>크기</Th></tr></thead>
          <tbody>
            {c.tables.map((t) => (
              <tr key={t.table} className="border-b border-line last:border-0">
                <Td className="font-mono text-[13px]">{t.table}</Td>
                <Td className="tabular-nums">{t.rows.toLocaleString()}</Td>
                <Td className="text-muted">{bytes(t.bytes)}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Card>
        <H>보존 정책 · 수동 정리</H>
        <div className="text-[13px] text-muted">실행 이력 보존 {c.settings.run_retention_days}일 · 완료 카드 아카이브 {c.settings.project_archive_days}일</div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Act onClick={() => prune.mutate()} disabled={prune.isPending}>지금 실행 이력 정리</Act>
          <Act onClick={() => archive.mutate()} disabled={archive.isPending}>지금 완료 카드 아카이브</Act>
        </div>
        {msg && <div className="mt-2 text-[13px] font-bold text-active">{msg}</div>}
      </Card>
    </div>
  )
}

/* ─────────── 공통 UI ─────────── */
function Loading() { return <p className="text-sm text-muted">불러오는 중…</p> }
function Err() { return <p className="text-sm font-semibold text-cancelled">불러오지 못했습니다</p> }
function Empty({ text = '데이터 없음' }: { text?: string }) { return <div className="py-6 text-center text-[13px] font-medium text-muted">{text}</div> }
function Th({ children }: { children: React.ReactNode }) { return <th className="px-3 py-2.5 font-bold">{children}</th> }
function Td({ children, className }: { children: React.ReactNode; className?: string }) { return <td className={cn('px-3 py-2.5 align-top', className)}>{children}</td> }
function Card({ children, className }: { children: React.ReactNode; className?: string }) { return <div className={cn('rounded-2xl border border-line bg-surface p-4', className)}>{children}</div> }
function H({ children }: { children: React.ReactNode }) { return <div className="mb-3 text-[13px] font-bold text-muted">{children}</div> }
function Pill({ children, className }: { children: React.ReactNode; className?: string; on?: boolean }) {
  return <span className={cn('rounded-full px-2 py-0.5 text-[11px] font-bold', className)}>{children}</span>
}
function Act({ children, onClick, disabled }: { children: React.ReactNode; onClick: () => void; disabled?: boolean }) {
  return <button onClick={onClick} disabled={disabled} className="rounded-lg border border-line px-2.5 py-1 text-xs font-bold text-muted hover:bg-line/50 disabled:opacity-50">{children}</button>
}
function Kpi({ value, label, danger, small }: { value: React.ReactNode; label: string; danger?: boolean; small?: boolean }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className={cn('font-extrabold', small ? 'text-lg' : 'text-2xl', danger ? 'text-cancelled' : 'text-primary')}>{value}</div>
      <div className="mt-0.5 text-[13px] font-semibold text-muted">{label}</div>
    </div>
  )
}
function statusCls(s: string) {
  return s === 'active' ? 'bg-active/15 text-active' : s === 'error' ? 'bg-cancelled/15 text-cancelled' : 'bg-onhold/15 text-onhold'
}
function statusLabel(s: string) {
  return s === 'active' ? '정상' : s === 'error' ? '오류' : s === 'configuring' ? '설정 중' : s
}
