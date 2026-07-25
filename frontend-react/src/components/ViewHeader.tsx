import { useState, type ReactNode } from 'react'
import { Settings } from 'lucide-react'
import type { AgentInfo } from '@/lib/types'
import { SettingsDialog } from '@/components/SettingsDialog'

/** 모든 뷰 상단 공통 헤더: 제목 + 액션 + 설정 버튼(에이전트 전달 시 설정 다이얼로그). */
export function ViewHeader({ title, actions, agent }: { title: string; actions?: ReactNode; agent?: AgentInfo }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="flex items-center gap-2 border-b border-line px-6 py-4">
      <h1 className="flex-1 truncate text-xl font-extrabold tracking-tight">{title}</h1>
      {actions}
      {agent && (
        <button aria-label="설정" onClick={() => setOpen(true)} className="grid h-9 w-9 place-items-center rounded-xl text-muted hover:bg-line/50">
          <Settings size={18} />
        </button>
      )}
      {open && agent && <SettingsDialog agent={agent} onClose={() => setOpen(false)} />}
    </div>
  )
}
