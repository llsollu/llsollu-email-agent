import { ClipboardList, History, Mails, Send, type LucideProps } from 'lucide-react'

// view_type → 성격에 맞는 아이콘. 브랜드 기본은 Mails.
const MAP = {
  kanban: ClipboardList, // 이슈 관리(보드)
  timeline: History, // 타임라인(히스토리)
  scheduler_panel: Send, // 자동 발송
} as const

export function AgentIcon({ viewType, ...props }: { viewType?: string | null } & LucideProps) {
  const Icon = MAP[viewType as keyof typeof MAP] ?? Mails
  return <Icon {...props} />
}

export { Mails as BrandIcon }
