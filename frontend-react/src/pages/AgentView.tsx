import { useParams } from 'react-router-dom'
import { useAgents } from '@/hooks/useAgents'
import { ViewHeader } from '@/components/ViewHeader'
import { Kanban } from '@/pages/Kanban'

export function AgentView() {
  const { id } = useParams()
  const agents = useAgents()
  const agent = agents.data?.find((a) => a.id === id)

  if (!agent) return <div className="grid h-full place-items-center text-muted">에이전트를 찾을 수 없습니다</div>

  if (agent.view_type === 'kanban') return <Kanban agent={agent} />

  // 스케줄러 뷰는 Phase 3
  return (
    <div className="flex h-full flex-col">
      <ViewHeader title={agent.name} />
      <div className="grid flex-1 place-items-center">
        <div className="text-center">
          <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-primary/10 text-2xl text-primary">발</div>
          <p className="text-lg font-bold">{agent.name}</p>
          <p className="mt-1 text-sm font-medium text-muted">스케줄러 뷰는 Phase 3에서 구현됩니다.</p>
        </div>
      </div>
    </div>
  )
}
