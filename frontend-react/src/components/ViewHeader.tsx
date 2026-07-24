import type { ReactNode } from 'react'
import { Settings } from 'lucide-react'

/** 모든 뷰 상단 공통 헤더: 제목 + 액션 + 설정 버튼. */
export function ViewHeader({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <div className="flex items-center gap-2 border-b border-line px-6 py-4">
      <h1 className="flex-1 truncate text-xl font-extrabold tracking-tight">{title}</h1>
      {actions}
      <button
        aria-label="설정"
        title="설정 (Phase 3)"
        className="grid h-9 w-9 place-items-center rounded-xl text-muted hover:bg-line/50"
      >
        <Settings size={18} />
      </button>
    </div>
  )
}
