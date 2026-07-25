import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Play, RefreshCw, Search, X } from 'lucide-react'
import { api } from '@/lib/api'
import type { AgentInfo, TimelineEntry } from '@/lib/types'
import { ViewHeader } from '@/components/ViewHeader'
import { SourceEmail } from '@/components/SourceEmail'
import { useEscape } from '@/lib/useEscape'
import { cn } from '@/lib/utils'

const PALETTE = ['#14b8a6', '#0ea5e9', '#f59e0b', '#8b5cf6', '#ff6b57', '#22c55e', '#e11d48', '#64748b']

function fmtTime(iso?: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(+d)) return ''
  const k = new Date(d.getTime() + 9 * 3600 * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(k.getUTCMonth() + 1)}/${p(k.getUTCDate())} ${p(k.getUTCHours())}:${p(k.getUTCMinutes())}`
}
function monthKey(iso?: string | null) {
  if (!iso) return '기타'
  const d = new Date(iso)
  if (isNaN(+d)) return '기타'
  const k = new Date(d.getTime() + 9 * 3600 * 1000)
  return `${k.getUTCFullYear()}. ${k.getUTCMonth() + 1}월`
}

export function Timeline({ agent }: { agent: AgentInfo }) {
  const tl = useQuery({ queryKey: ['timeline', agent.id], queryFn: () => api.timeline(agent.id), refetchInterval: 60_000 })
  const [group, setGroup] = useState<'client' | 'project'>(
    ((agent.config.default_group as string) === 'project' ? 'project' : 'client'),
  )
  const [cat, setCat] = useState('')
  const [sel, setSel] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [origin, setOrigin] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const all = useMemo(() => tl.data ?? [], [tl.data])
  const keyOf = (e: TimelineEntry) => (group === 'client' ? e.client_name : e.project_title) || '(미분류)'

  const categories = useMemo(
    () => [...new Set(all.map((e) => e.category).filter(Boolean) as string[])].sort(),
    [all],
  )
  const catColor = (c?: string | null) => (c ? PALETTE[categories.indexOf(c) % PALETTE.length] : '#64748b')

  const groups = useMemo(() => {
    const m: Record<string, number> = {}
    all.forEach((e) => { m[keyOf(e)] = (m[keyOf(e)] || 0) + 1 })
    return Object.entries(m).sort((a, b) => b[1] - a[1])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [all, group])

  const rows = useMemo(() => {
    const q = query.toLowerCase()
    return all
      .filter((e) => {
        if (cat && (e.category ?? '') !== cat) return false
        if (sel && keyOf(e) !== sel) return false
        if (q && !`${e.subject}${e.summary}${e.client_name}${e.project_title}`.toLowerCase().includes(q)) return false
        return true
      })
      .sort((a, b) => (b.received_at ?? '').localeCompare(a.received_at ?? ''))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [all, cat, sel, query, group])

  async function dryRun() {
    await api.runNow(agent.id, false) // 타임라인은 저장(공유 분석)해야 화면에 쌓이므로 실제 실행
    setToast('최신 메일 분석을 큐에 넣었습니다')
    setTimeout(() => setToast(null), 3000)
    setTimeout(() => tl.refetch(), 3000)
  }

  const toggle = (id: string) =>
    setExpanded((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n })

  let lastMonth = ''

  return (
    <div className="flex h-full flex-col">
      <ViewHeader
        title={agent.name}
        agent={agent}
        actions={
          <>
            <button onClick={dryRun} className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-bold text-primary hover:bg-primary/10">
              <Play size={16} /> 최신 메일 분석
            </button>
            <button onClick={() => tl.refetch()} aria-label="새로고침" className="grid h-9 w-9 place-items-center rounded-xl text-muted hover:bg-line/50">
              <RefreshCw size={17} />
            </button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-3 px-6 pt-4">
        <div className="relative">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="제목 · 요약 · 고객사 검색…"
            className="w-64 rounded-xl border border-line bg-surface py-2 pl-9 pr-3 text-sm outline-none focus:border-primary" />
        </div>
        <div className="inline-flex rounded-xl border border-line p-1">
          {(['client', 'project'] as const).map((g) => (
            <button key={g} onClick={() => { setGroup(g); setSel(null) }}
              className={cn('rounded-lg px-4 py-1.5 text-sm font-bold', group === g ? 'bg-primary text-white' : 'text-muted hover:bg-line/50')}>
              {g === 'client' ? '고객사별' : '프로젝트별'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 px-6 py-3">
        {['전체', ...categories].map((c) => {
          const on = (c === '전체' && !cat) || c === cat
          const col = c === '전체' ? '#14b8a6' : catColor(c)
          return (
            <button key={c} onClick={() => setCat(c === '전체' ? '' : c)}
              className={cn('rounded-full border px-3 py-1 text-[13px] font-bold', on ? 'border-transparent text-white' : 'border-line bg-surface text-muted')}
              style={on ? { background: col } : undefined}>
              {c}
            </button>
          )
        })}
      </div>

      <div className="grid flex-1 grid-cols-[220px_1fr] gap-5 overflow-hidden px-6 pb-6">
        {/* 그룹 레일 */}
        <div className="overflow-y-auto">
          <div className="px-2 py-1 text-xs font-extrabold uppercase tracking-wide text-muted">{group === 'client' ? '고객사' : '프로젝트'}</div>
          {groups.map(([k, n]) => (
            <button key={k} onClick={() => setSel(sel === k ? null : k)}
              className={cn('flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-sm font-bold', sel === k ? 'bg-primary/10 text-primary' : 'hover:bg-line/50')}>
              <span className="truncate">{k}</span>
              <span className="ml-auto rounded-full border border-line bg-surface px-2 text-xs font-extrabold text-muted">{n}</span>
            </button>
          ))}
        </div>

        {/* 타임라인 */}
        <div className="overflow-y-auto pr-1">
          {tl.isLoading && <p className="p-4 text-muted">불러오는 중…</p>}
          {tl.isError && <p className="p-4 font-semibold text-cancelled">타임라인을 불러오지 못했습니다</p>}
          {tl.data && rows.length === 0 && <p className="p-8 text-center font-medium text-muted">조건에 맞는 메일이 없습니다</p>}
          <div className="relative pl-6">
            {rows.length > 0 && <div className="absolute bottom-2 left-[9px] top-2 w-0.5 rounded bg-line" />}
            {rows.map((e) => {
              const m = monthKey(e.received_at)
              const head = m !== lastMonth ? ((lastMonth = m), m) : null
              const col = catColor(e.category)
              const open = expanded.has(e.id)
              return (
                <div key={e.id}>
                  {head && <div className="sticky top-0 z-[1] bg-bg py-2 text-xs font-extrabold text-muted">{head}</div>}
                  <div className="relative mb-3">
                    <span className="absolute -left-[21px] top-4 h-3 w-3 rounded-full border-[3px] border-bg" style={{ background: col }} />
                    <div className="cursor-pointer rounded-2xl border border-line bg-surface p-3.5 transition hover:shadow-[var(--shadow)]" onClick={() => toggle(e.id)}>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-bold tabular-nums text-muted">{fmtTime(e.received_at)}</span>
                        <span className={cn('rounded-full px-2 py-0.5 text-[11px] font-extrabold', e.direction === 'out' ? 'bg-muted/20 text-muted' : 'bg-brand2/15 text-brand2')}>
                          {e.direction === 'out' ? '발신' : '수신'}
                        </span>
                        {e.category && (
                          <span className="rounded-full px-2 py-0.5 text-[11px] font-extrabold" style={{ background: `color-mix(in srgb, ${col} 16%, transparent)`, color: col }}>{e.category}</span>
                        )}
                        {e.issue && <span className="ml-auto rounded-full bg-accent/15 px-2 py-0.5 text-[11px] font-extrabold text-accent">이슈</span>}
                      </div>
                      <div className="mt-1.5 font-extrabold">{e.subject || '(제목 없음)'}</div>
                      <div className="text-xs font-medium text-muted">{e.from_name || e.from_address} · {e.client_name || '-'} / {e.project_title || '-'}</div>
                      {e.summary && <div className="mt-1.5 text-[13px] font-medium leading-relaxed">{e.summary}</div>}
                      {open && (
                        <div className="mt-2.5 border-t border-dashed border-line pt-2.5">
                          {(e.points ?? []).map((p, i) => (
                            <div key={i} className="relative py-0.5 pl-3.5 text-[13px] font-medium text-muted before:absolute before:left-0.5 before:top-2 before:h-1 before:w-1 before:rounded-full before:bg-primary">{p}</div>
                          ))}
                          <button
                            onClick={(ev) => { ev.stopPropagation(); setOrigin(e.id) }}
                            className="mt-2 text-xs font-extrabold text-primary hover:underline"
                          >
                            원문 메일 보기 →
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {origin && <OriginModal agentId={agent.id} messageId={origin} onClose={() => setOrigin(null)} />}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-surface shadow-lg">{toast}</div>
      )}
    </div>
  )
}

function OriginModal({ agentId, messageId, onClose }: { agentId: string; messageId: string; onClose: () => void }) {
  useEscape(onClose)
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-6" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-line bg-surface p-6 shadow-[var(--shadow)]" onClick={(e) => e.stopPropagation()}>
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-lg font-extrabold">원문 메일</h2>
          <button aria-label="닫기" onClick={onClose} className="text-muted hover:text-ink"><X size={20} /></button>
        </div>
        <SourceEmail agentId={agentId} messageId={messageId} />
        <div className="mt-4 text-right">
          <button onClick={onClose} className="rounded-xl px-4 py-2 font-semibold text-muted hover:bg-line/50">닫기</button>
        </div>
      </div>
    </div>
  )
}
