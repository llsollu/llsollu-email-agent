import { useState } from 'react'
import { useParams } from 'react-router-dom'
import type { AgentInfo } from '@/lib/types'
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

/** 여러 뷰를 탭으로 전환하는 워크스페이스(설정 1번, 대시보드 여러 개). */
function Workspace({ agent }: { agent: AgentInfo }) {
  const views = agent.views!
  const [type, setType] = useState(views[0].type)
  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 border-b border-line px-6 pt-2">
        {views.map((v) => (
          <button
            key={v.key}
            onClick={() => setType(v.type)}
            className={cn(
              '-mb-px rounded-t-lg border-b-2 px-4 py-2 text-sm font-bold transition',
              type === v.type ? 'border-primary text-primary' : 'border-transparent text-muted hover:text-ink',
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
