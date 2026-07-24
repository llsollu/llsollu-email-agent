import { useParams } from 'react-router-dom'
import { useAgents } from '@/hooks/useAgents'
import { ViewHeader } from '@/components/ViewHeader'

/** Phase 1 자리표시자. 실제 칸반/스케줄러 뷰는 Phase 2/3에서 구현. */
export function AgentView() {
  const { id } = useParams()
  const agents = useAgents()
  const agent = agents.data?.find((a) => a.id === id)

  if (!agent) return <div className="grid h-full place-items-center text-muted">에이전트를 찾을 수 없습니다</div>

  const phase = agent.view_type === 'kanban' ? 'Phase 2 (칸반)' : 'Phase 3 (스케줄러)'
  return (
    <div className="flex h-full flex-col">
      <ViewHeader title={agent.name} />
      <div className="grid flex-1 place-items-center">
        <div className="text-center">
          <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-primary/10 text-2xl text-primary">
            {agent.view_type === 'kanban' ? '분' : '발'}
          </div>
          <p className="text-lg font-bold">{agent.name}</p>
          <p className="mt-1 text-sm font-medium text-muted">이 뷰는 {phase}에서 구현됩니다.</p>
        </div>
      </div>
    </div>
  )
}
