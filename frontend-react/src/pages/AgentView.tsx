import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import type { AgentInfo, AgentView as AgentViewSpec } from '@/lib/types'
import { useAgents } from '@/hooks/useAgents'
import { Kanban } from '@/pages/Kanban'
import { Scheduler } from '@/pages/Scheduler'
import { Timeline } from '@/pages/Timeline'
import { cn } from '@/lib/utils'

export function AgentView() {
  const { id } = useParams()
  const agents = useAgents()
  const agent = agents.data?.find((a) => a.id === id)

  if (!agent) return <div className="grid h-full place-items-center text-muted">에이전트를 찾을 수 없습니다</div>
  if ((agent.views?.length ?? 0) > 1) return <Workspace agent={agent} />
  return <SingleView agent={agent} type={agent.view_type ?? ''} />
}

function SingleView({ agent, type }: { agent: AgentInfo; type: string }) {
  if (type === 'kanban') return <Kanban agent={agent} />
  if (type === 'timeline') return <Timeline agent={agent} />
  return <Scheduler agent={agent} />
}

/** 여러 뷰를 탭으로 전환하는 워크스페이스(설정 1번, 대시보드 여러 개).
 *  패널 이름(탭)을 드래그해 서로 위치를 바꿀 수 있고, 순서는 로컬에 저장된다. */
function Workspace({ agent }: { agent: AgentInfo }) {
  const views = agent.views!
  const orderKey = `agent-view-order:${agent.id}`

  const [order, setOrder] = useState<string[]>(() => {
    const saved = readOrder(orderKey)
    const keys = views.map((v) => v.key)
    // 저장된 순서 중 현재 유효한 것만 + 새로 생긴 뷰는 뒤에 붙인다.
    const merged = [...saved.filter((k) => keys.includes(k)), ...keys.filter((k) => !saved.includes(k))]
    return merged.length ? merged : keys
  })
  const ordered = useMemo(
    () => order.map((k) => views.find((v) => v.key === k)).filter(Boolean) as AgentViewSpec[],
    [order, views],
  )
  const [type, setType] = useState(ordered[0]?.type ?? views[0].type)
  const [dragKey, setDragKey] = useState<string | null>(null)

  function reorder(from: string, to: string) {
    if (from === to) return
    setOrder((prev) => {
      const next = [...prev]
      const fi = next.indexOf(from)
      const ti = next.indexOf(to)
      if (fi < 0 || ti < 0) return prev
      next.splice(fi, 1)
      next.splice(ti, 0, from)
      writeOrder(orderKey, next)
      return next
    })
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 border-b border-line px-6 pt-2">
        {ordered.map((v) => (
          <button
            key={v.key}
            draggable
            onDragStart={() => setDragKey(v.key)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => { if (dragKey) reorder(dragKey, v.key); setDragKey(null) }}
            onDragEnd={() => setDragKey(null)}
            onClick={() => setType(v.type)}
            title="드래그해서 패널 순서를 바꿀 수 있어요"
            className={cn(
              '-mb-px cursor-grab rounded-t-lg border-b-2 px-4 py-2 text-sm font-bold transition active:cursor-grabbing',
              type === v.type ? 'border-primary text-primary' : 'border-transparent text-muted hover:text-ink',
              dragKey === v.key && 'opacity-40',
            )}
          >
            {v.label}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1">
        <SingleView agent={agent} type={type} />
      </div>
    </div>
  )
}

function readOrder(key: string): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(key) ?? '[]')
    return Array.isArray(v) ? v.filter((x) => typeof x === 'string') : []
  } catch {
    return []
  }
}
function writeOrder(key: string, order: string[]) {
  try {
    localStorage.setItem(key, JSON.stringify(order))
  } catch {
    /* ignore */
  }
}
