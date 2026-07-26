import { useMemo, useState } from 'react'
import {
  DndContext, DragOverlay, PointerSensor, useDraggable, useDroppable, useSensor, useSensors,
  type DragEndEvent, type DragStartEvent,
} from '@dnd-kit/core'
import { Mail, RefreshCw, Search, X } from 'lucide-react'
import type { AgentInfo, ProjectInfo } from '@/lib/types'
import { useMoveProject, useProjects } from '@/hooks/useProjects'
import { ViewHeader } from '@/components/ViewHeader'
import { AnalyzeButton } from '@/components/AnalyzeButton'
import { SourceEmail } from '@/components/SourceEmail'
import { issueLabelMap, type IssueType } from '@/lib/issueTypes'
import { useEscape } from '@/lib/useEscape'
import { cn, receiptBadge } from '@/lib/utils'

const COLUMNS: [string, string, string][] = [
  ['storyboard', '스토리보드', 'bg-storyboard'],
  ['active', '진행 중', 'bg-active'],
  ['on_hold', '보류', 'bg-onhold'],
  ['completed', '완료', 'bg-completed'],
]
const STATUS_LABEL: Record<string, string> = Object.fromEntries(COLUMNS.map((c) => [c[0], c[1]]))
const STATUS_BADGE: Record<string, string> = {
  storyboard: 'bg-storyboard/15 text-storyboard',
  active: 'bg-active/15 text-active',
  on_hold: 'bg-onhold/15 text-onhold',
  completed: 'bg-completed/15 text-completed',
  cancelled: 'bg-cancelled/15 text-cancelled',
}
const SEVERITY: Record<string, string> = { critical: '치명', high: '높음', medium: '보통', low: '낮음' }

function fmtDate(iso?: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(+d)) return ''
  const k = new Date(d.getTime() + 9 * 3600 * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(k.getUTCMonth() + 1)}/${p(k.getUTCDate())} ${p(k.getUTCHours())}:${p(k.getUTCMinutes())}`
}

export function Kanban({ agent }: { agent: AgentInfo }) {
  const projects = useProjects(agent.id)
  const move = useMoveProject(agent.id)
  const [query, setQuery] = useState('')
  const [catFilter, setCatFilter] = useState('')
  const [sortBy, setSortBy] = useState('updated')
  const [detail, setDetail] = useState<ProjectInfo | null>(null)
  const [dragId, setDragId] = useState<string | null>(null)

  const titleField = (agent.config.primary_axis as string) || 'client'
  const issueLabels = useMemo(() => issueLabelMap(agent.config.issue_types as IssueType[] | undefined), [agent.config.issue_types])
  const all = useMemo(() => projects.data ?? [], [projects.data])

  const categories = useMemo(
    () => [...new Set(all.map((p) => p.category).filter(Boolean) as string[])].sort(),
    [all],
  )

  const visible = useMemo(() => {
    const q = query.toLowerCase()
    const list = all.filter((p) => {
      if (q) {
        const hay = [
          p.client_name, p.title, p.category, p.latest_update,
          ...(p.keywords ?? []),
          ...p.issues.map((i) => i.summary),
        ].filter(Boolean).join(' ').toLowerCase()
        if (!hay.includes(q)) return false
      }
      if (catFilter && (p.category ?? '') !== catFilter) return false
      return true
    })
    list.sort((a, b) => {
      if (sortBy === 'category') return (a.category ?? '').localeCompare(b.category ?? '')
      if (sortBy === 'client') return a.client_name.localeCompare(b.client_name)
      return (b.updated_at ?? '').localeCompare(a.updated_at ?? '')
    })
    return list
  }, [all, query, catFilter, sortBy])

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

  function onDragEnd(e: DragEndEvent) {
    setDragId(null)
    const id = e.active.id as string
    const target = e.over?.id as string | undefined
    if (!target) return
    const p = all.find((x) => x.id === id)
    if (p && p.status !== target) move.mutate({ id, status: target })
  }

  const dragged = all.find((p) => p.id === dragId)

  return (
    <div className="flex h-full flex-col">
      <ViewHeader
        title={agent.name}
        agent={agent}
        actions={
          <>
            <AnalyzeButton agentId={agent.id} />
            <button
              onClick={() => projects.refetch()}
              aria-label="새로고침"
              className="grid h-9 w-9 place-items-center rounded-xl text-muted hover:bg-line/50"
            >
              <RefreshCw size={17} />
            </button>
          </>
        }
      />

      <Toolbar
        query={query} setQuery={setQuery}
        categories={categories} catFilter={catFilter} setCatFilter={setCatFilter}
        sortBy={sortBy} setSortBy={setSortBy}
      />
      <StatRow projects={visible} />

      {projects.isLoading ? (
        <div className="grid flex-1 place-items-center text-muted">불러오는 중…</div>
      ) : projects.isError ? (
        <div className="grid flex-1 place-items-center">
          <div className="text-center">
            <p className="font-semibold text-cancelled">프로젝트를 불러오지 못했습니다</p>
            <button onClick={() => projects.refetch()} className="mt-2 rounded-xl bg-primary px-4 py-2 font-bold text-white">다시 시도</button>
          </div>
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          onDragStart={(e: DragStartEvent) => setDragId(e.active.id as string)}
          onDragEnd={onDragEnd}
          onDragCancel={() => setDragId(null)}
        >
          <div className="flex flex-1 gap-4 overflow-x-auto px-5 pb-5">
            {COLUMNS.map(([status, label, bar]) => (
              <Column
                key={status}
                status={status} label={label} bar={bar}
                cards={visible.filter((p) => p.status === status)}
                titleField={titleField}
                issueLabels={issueLabels}
                onOpen={setDetail}
              />
            ))}
          </div>
          <DragOverlay>
            {dragged && <CardBody p={dragged} titleField={titleField} issueLabels={issueLabels} dragging />}
          </DragOverlay>
        </DndContext>
      )}

      {detail && <DetailModal p={detail} agentId={agent.id} issueLabels={issueLabels} onClose={() => setDetail(null)} />}
    </div>
  )
}

function Toolbar(props: {
  query: string; setQuery: (v: string) => void
  categories: string[]; catFilter: string; setCatFilter: (v: string) => void
  sortBy: string; setSortBy: (v: string) => void
}) {
  const sel = 'rounded-xl border border-line bg-surface px-3 py-2 text-sm font-medium outline-none focus:border-primary'
  return (
    <div className="flex flex-wrap items-center gap-3 px-5 py-3">
      <div className="relative">
        <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          value={props.query} onChange={(e) => props.setQuery(e.target.value)}
          placeholder="분석 / 요약 내용 검색…"
          className="w-60 rounded-xl border border-line bg-surface py-2 pl-9 pr-3 text-sm outline-none focus:border-primary"
        />
      </div>
      <select value={props.catFilter} onChange={(e) => props.setCatFilter(e.target.value)} className={sel}>
        <option value="">전체 분류</option>
        {props.categories.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
      <select value={props.sortBy} onChange={(e) => props.setSortBy(e.target.value)} className={sel}>
        <option value="updated">최근 업데이트 순</option>
        <option value="category">분류 순</option>
        <option value="client">고객사명 순</option>
      </select>
    </div>
  )
}

function StatRow({ projects }: { projects: ProjectInfo[] }) {
  const active = projects.filter((p) => p.status === 'active').length
  const onhold = projects.filter((p) => p.status === 'on_hold').length
  const issues = projects.filter((p) => p.issues.some((i) => i.status !== 'resolved')).length
  const box = (v: number, l: string, danger = false) => (
    <div className="rounded-2xl border border-line bg-surface px-5 py-3">
      <div className={cn('text-2xl font-extrabold', danger ? 'text-cancelled' : 'text-primary')}>{v}</div>
      <div className="text-[13px] font-semibold text-muted">{l}</div>
    </div>
  )
  return (
    <div className="flex flex-wrap gap-3 px-5 pb-3">
      {box(projects.length, '전체 이슈')}
      {box(active, '진행 중')}
      {box(onhold, '보류')}
      {box(issues, '미해결 이슈', true)}
    </div>
  )
}

function Column({
  status, label, bar, cards, titleField, issueLabels, onOpen,
}: {
  status: string; label: string; bar: string; cards: ProjectInfo[]; titleField: string
  issueLabels: Record<string, string>
  onOpen: (p: ProjectInfo) => void
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status })
  return (
    <div className="flex w-[300px] shrink-0 flex-col rounded-2xl border border-line bg-line/40">
      <div className={cn('h-[3px] rounded-t-2xl', bar)} />
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-sm font-extrabold">{label}</span>
        <span className="rounded-full border border-line bg-surface px-2 py-0.5 text-xs font-extrabold text-muted">{cards.length}</span>
      </div>
      <div
        ref={setNodeRef}
        className={cn(
          'mx-2 mb-2 flex-1 overflow-y-auto rounded-lg p-1 transition',
          isOver && 'bg-primary/10 outline-2 outline-dashed outline-primary',
        )}
      >
        {cards.length === 0 ? (
          <div className="py-6 text-center text-[13px] font-medium text-muted">카드를 여기로 드래그</div>
        ) : (
          cards.map((p) => <DraggableCard key={p.id} p={p} titleField={titleField} issueLabels={issueLabels} onOpen={onOpen} />)
        )}
      </div>
    </div>
  )
}

function DraggableCard({ p, titleField, issueLabels, onOpen }: { p: ProjectInfo; titleField: string; issueLabels: Record<string, string>; onOpen: (p: ProjectInfo) => void }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: p.id })
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={() => onOpen(p)}
      className={cn('mb-2 cursor-grab active:cursor-grabbing', isDragging && 'opacity-40')}
    >
      <CardBody p={p} titleField={titleField} issueLabels={issueLabels} />
    </div>
  )
}

function senderText(p: ProjectInfo) {
  return p.from_name || p.from_address || ''
}
function primaryText(p: ProjectInfo, axis: string) {
  if (axis === 'sender') return senderText(p) || '(발신인 미상)'
  return axis === 'project' ? p.title : p.client_name
}
function secondaryText(p: ProjectInfo, axis: string) {
  if (axis === 'sender') return p.client_name || p.title
  return axis === 'project' ? p.client_name : p.title
}
function priorityColor(pr?: string | null) {
  return pr === 'critical' ? 'bg-cancelled' : pr === 'high' ? 'bg-onhold' : pr === 'low' ? 'bg-muted' : 'bg-primary'
}

function CardBody({ p, titleField, issueLabels, dragging }: { p: ProjectInfo; titleField: string; issueLabels: Record<string, string>; dragging?: boolean }) {
  const open = p.issues.filter((i) => i.status !== 'resolved')
  return (
    <div className={cn('rounded-xl border border-line bg-surface p-3.5', dragging && 'shadow-[var(--shadow)]')}>
      <div className="flex items-start">
        <div className="min-w-0 flex-1">
          <div className="font-extrabold">{primaryText(p, titleField)}</div>
          <div className="truncate text-[13px] font-medium text-muted">{secondaryText(p, titleField)}</div>
          {titleField !== 'sender' && senderText(p) && (
            <div className="mt-1 flex items-center gap-1 truncate text-[12px] font-medium text-muted">
              <Mail size={12} className="shrink-0" /> <span className="truncate">{senderText(p)}</span>
            </div>
          )}
        </div>
        <span className={cn('mt-1.5 ml-1.5 h-2 w-2 shrink-0 rounded-full', priorityColor(p.priority))} />
      </div>
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {p.category && <Badge className="bg-primary/10 text-primary">{p.category}</Badge>}
        <Badge className={receiptBadge(p.recipient_role).cls}>{receiptBadge(p.recipient_role).label}</Badge>
      </div>
      {p.latest_update && (
        <p className="mt-2.5 border-l-[3px] border-line pl-2 text-[13px] font-medium text-muted line-clamp-3">{p.latest_update}</p>
      )}
      {open.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {open.slice(0, 3).map((i) => (
            <Badge key={i.id} className="bg-cancelled/15 text-cancelled">
              {(issueLabels[i.type] ?? i.type)}: {i.summary.length > 18 ? i.summary.slice(0, 18) + '…' : i.summary}
            </Badge>
          ))}
        </div>
      )}
      {p.updated_at && <div className="mt-2.5 text-right text-xs font-medium text-muted">{fmtDate(p.updated_at)}</div>}
    </div>
  )
}

function Badge({ children, className }: { children: React.ReactNode; className?: string }) {
  return <span className={cn('rounded-full px-2.5 py-1 text-xs font-bold', className)}>{children}</span>
}

function DetailModal({ p, agentId, issueLabels, onClose }: { p: ProjectInfo; agentId: string; issueLabels: Record<string, string>; onClose: () => void }) {
  useEscape(onClose)
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 px-6" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl border border-line bg-surface p-6 shadow-[var(--shadow)]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-lg font-extrabold">{p.client_name} — {p.title}</h2>
          <button aria-label="닫기" onClick={onClose} className="text-muted hover:text-ink"><X size={20} /></button>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {p.category && <Badge className="bg-primary/10 text-primary">{p.category}</Badge>}
          <Badge className={STATUS_BADGE[p.status]}>{STATUS_LABEL[p.status] ?? p.status}</Badge>
        </div>
        {p.latest_update && <p className="mt-3 text-sm font-medium">{p.latest_update}</p>}
        <div className="mt-5 text-sm font-extrabold">이슈 목록</div>
        <div className="mt-2 space-y-2">
          {p.issues.length === 0 ? (
            <p className="text-sm font-medium text-muted">이슈 없음</p>
          ) : (
            p.issues.map((i) => (
              <div key={i.id} className="rounded-lg border border-line p-2.5">
                <div className="text-sm font-semibold">{i.summary}</div>
                <div className="mt-1 text-[13px] font-medium text-muted">
                  유형: {issueLabels[i.type] ?? i.type} · 심각도: {SEVERITY[i.severity] ?? i.severity} ·
                  상태: {i.status === 'resolved' ? '해결됨' : i.status === 'in_progress' ? '처리 중' : '미해결'}
                </div>
              </div>
            ))
          )}
        </div>
        {p.source_message_id && <SourceEmail agentId={agentId} messageId={p.source_message_id} />}
        <div className="mt-5 text-right">
          <button onClick={onClose} className="rounded-xl px-4 py-2 font-semibold text-muted hover:bg-line/50">닫기</button>
        </div>
      </div>
    </div>
  )
}

