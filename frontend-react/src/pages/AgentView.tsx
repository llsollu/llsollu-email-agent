import { useParams } from 'react-router-dom'
import { useAgents } from '@/hooks/useAgents'
import { Kanban } from '@/pages/Kanban'
import { Scheduler } from '@/pages/Scheduler'
import { Timeline } from '@/pages/Timeline'

export function AgentView() {
  const { id } = useParams()
  const agents = useAgents()
  const agent = agents.data?.find((a) => a.id === id)

  if (!agent) return <div className="grid h-full place-items-center text-muted">에이전트를 찾을 수 없습니다</div>
  if (agent.view_type === 'kanban') return <Kanban agent={agent} />
  if (agent.view_type === 'timeline') return <Timeline agent={agent} />
  return <Scheduler agent={agent} />
}
