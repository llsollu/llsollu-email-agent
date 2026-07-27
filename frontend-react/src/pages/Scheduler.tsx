import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Play, RefreshCw } from 'lucide-react'
import { api } from '@/lib/api'
import type { AgentInfo, RunInfo } from '@/lib/types'
import { humanFromCron } from '@/lib/schedule'
import { ViewHeader } from '@/components/ViewHeader'
import { cn } from '@/lib/utils'

const TRIGGER: Record<string, string> = { schedule: '예약 실행', manual: '수동 실행', email: '메일 수신' }
const RUN_STATUS: Record<string, string> = { ok: '성공', error: '오류', running: '실행 중' }

function fmtKst(iso?: unknown) {
  if (typeof iso !== 'string') return '-'
  const d = new Date(iso)
  if (isNaN(+d)) return String(iso)
  const k = new Date(d.getTime() + 9 * 3600 * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${k.getUTCFullYear()}-${p(k.getUTCMonth() + 1)}-${p(k.getUTCDate())} ${p(k.getUTCHours())}:${p(k.getUTCMinutes())} (KST)`
}

/** 공유 URL에서 사람이 읽을 수 있는 파일 제목(파일명)을 추출. 못 찾으면 null. */
function fileTitleFromUrl(url: string): string | null {
  if (!url) return null
  try {
    const u = new URL(url)
    const byParam = u.searchParams.get('file') || u.searchParams.get('filename')
    if (byParam) return decodeURIComponent(byParam)
    const segs = u.pathname.split('/').map((s) => decodeURIComponent(s)).filter(Boolean)
    // 확장자가 있는 마지막 경로 세그먼트를 파일명으로 본다.
    for (let i = segs.length - 1; i >= 0; i--) {
      if (/\.[a-z0-9]{2,5}$/i.test(segs[i])) return segs[i]
    }
    return null
  } catch {
    return null
  }
}

export function Scheduler({ agent }: { agent: AgentInfo }) {
  const qc = useQueryClient()
  const cfg = agent.config as Record<string, unknown>
  const runs = useQuery({ queryKey: ['runs', agent.id], queryFn: () => api.runs(agent.id), refetchInterval: 30_000 })
  const schedule = useQuery({ queryKey: ['schedule', agent.id], queryFn: () => api.schedule(agent.id) })
  const [toast, setToast] = useState<string | null>(null)

  const toggle = useMutation({
    mutationFn: (enabled: boolean) => api.toggleSchedule(agent.id, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedule', agent.id] }),
  })

  async function dryRun() {
    await api.runNow(agent.id, true)
    setToast('드라이런 실행을 큐에 넣었습니다')
    setTimeout(() => setToast(null), 3000)
    setTimeout(() => runs.refetch(), 2500)
  }

  const sched = schedule.data as Record<string, unknown> | null
  const cc = String(cfg.cc_email ?? '')
  const dateCol = String(cfg.date_column ?? '')
  const fileUrl = String(cfg.sharepoint_file_url ?? '')
  const fileTitle = fileTitleFromUrl(fileUrl)

  return (
    <div className="flex h-full flex-col">
      <ViewHeader
        title={agent.name}
        agent={agent}
        actions={
          <>
            <button onClick={dryRun} className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-bold text-primary hover:bg-primary/10">
              <Play size={16} /> 지금 실행(드라이런)
            </button>
            <button onClick={() => runs.refetch()} aria-label="새로고침" className="grid h-9 w-9 place-items-center rounded-xl text-muted hover:bg-line/50">
              <RefreshCw size={17} />
            </button>
          </>
        }
      />

      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        <Section title="트리거 / 규칙">
          <Kv k="확인 주기" v={humanFromCron(String(cfg.cron ?? ''))} />
          <KvNode k="참조 파일">
            {fileUrl
              ? <a href={fileUrl} target="_blank" rel="noreferrer" className="font-semibold text-primary hover:underline">{fileTitle ?? fileUrl}</a>
              : <span className="font-medium text-muted">지정 안 함 (데이터 없이 발송)</span>}
          </KvNode>
          <Kv k="발신자" v={String(cfg.mail_sender ?? '-')} />
          <Kv k="수신자" v={String(cfg.recipient_email ?? '-')} />
          {cc && <Kv k="참조" v={cc} />}
          <Kv k="오류시 알림" v={String(cfg.alert_email || cfg.mail_sender || '-')} />
          <Kv k="발송기준일" v={dateCol ? `첨부 파일 내 데이터 - ${dateCol}` : '지정 안 함 (주기마다 전체 발송)'} />
        </Section>

        {sched && (
          <div className="rounded-2xl border border-line bg-surface p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-bold">스케줄 활성화</div>
                <div className="mt-0.5 text-sm font-medium text-muted">
                  확인 주기: {humanFromCron(String(cfg.cron ?? ''))}<br />
                  다음 실행: {fmtKst(sched.next_run_at)}
                </div>
              </div>
              <Toggle checked={sched.enabled === true} onChange={(v) => toggle.mutate(v)} />
            </div>
          </div>
        )}

        <div>
          <div className="mb-2 text-[15px] font-extrabold">최근 실행 로그</div>
          <div className="space-y-2">
            {runs.isLoading && <p className="text-sm font-medium text-muted">불러오는 중…</p>}
            {runs.isError && <p className="text-sm font-semibold text-cancelled">실행 로그를 불러오지 못했습니다</p>}
            {runs.data?.length === 0 && <p className="text-sm font-medium text-muted">아직 실행 이력이 없습니다</p>}
            {runs.data?.map((r) => <RunTile key={r.id} r={r} />)}
          </div>
        </div>
      </div>

      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-surface shadow-lg">
          {toast}
        </div>
      )}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className="mb-2 text-[15px] font-extrabold">{title}</div>
      <div className="space-y-1">{children}</div>
    </div>
  )
}

function Kv({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-3 py-0.5 text-sm">
      <span className="w-32 shrink-0 font-semibold text-muted">{k}</span>
      <span className="min-w-0 break-all font-medium">{v}</span>
    </div>
  )
}

function KvNode({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3 py-0.5 text-sm">
      <span className="w-32 shrink-0 font-semibold text-muted">{k}</span>
      <span className="min-w-0 break-all">{children}</span>
    </div>
  )
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      role="switch" aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn('relative h-7 w-12 rounded-full transition', checked ? 'bg-primary' : 'bg-line')}
    >
      <span className={cn('absolute top-1 h-5 w-5 rounded-full bg-white transition', checked ? 'left-6' : 'left-1')} />
    </button>
  )
}

function RunTile({ r }: { r: RunInfo }) {
  const s = r.stats
  const isDry = s.dry_run === true
  const dot = r.status === 'ok' ? 'bg-active' : r.status === 'error' ? 'bg-cancelled' : 'bg-onhold'
  const parts: string[] = []
  if (s.total !== undefined) parts.push(`총 ${s.total}건`)
  if (s.targets !== undefined) parts.push(`발송 대상 ${s.targets}건`)
  if (isDry) parts.push('드라이런(실제 발송 안 함)')
  else {
    if (s.sent !== undefined) parts.push(`발송 ${s.sent}건`)
    if (s.failed) parts.push(`실패 ${s.failed}건`)
  }
  const events = (s.events as Record<string, unknown>[]) ?? []
  const details: string[] = []
  for (const e of events) {
    if (e.event === 'send_failed') details.push(`· 발송 실패 (${e.to}): ${e.error}`)
    if (e.event === 'dry_run') details.push(`· [미리보기] 제목: ${e.subject}`)
  }
  return (
    <div className="rounded-2xl border border-line bg-surface p-3">
      <div className="flex items-center gap-2">
        <span className={cn('h-2.5 w-2.5 rounded-full', dot)} />
        <span className="font-bold">{TRIGGER[r.trigger_source] ?? r.trigger_source} · {RUN_STATUS[r.status] ?? r.status}</span>
        <span className="ml-auto shrink-0 text-xs font-medium text-muted">{fmtKst(r.started_at)}</span>
      </div>
      <div className="mt-1 pl-4.5 text-sm">
        <div className="font-medium">{parts.length ? parts.join(' · ') : '기록 없음'}</div>
        {r.error && <div className="font-semibold text-cancelled">오류: {r.error}</div>}
        {details.slice(0, 5).map((d, i) => <div key={i} className="text-[13px] font-medium text-muted">{d}</div>)}
      </div>
    </div>
  )
}
