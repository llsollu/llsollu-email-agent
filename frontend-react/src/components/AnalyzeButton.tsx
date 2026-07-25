import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { api } from '@/lib/api'

/**
 * 이슈 보드·타임라인 공통 "최신 메일 분석" 버튼.
 * 최신 메일을 실제로 분석·저장(공유 분석)하여 두 대시보드에 함께 반영한다.
 */
export function AnalyzeButton({ agentId }: { agentId: string }) {
  const qc = useQueryClient()
  const [toast, setToast] = useState<string | null>(null)

  async function run() {
    try {
      await api.runNow(agentId, false) // 실제 실행: 공유 분석을 저장해야 두 뷰에 쌓인다
      setToast('최신 메일 분석을 시작했습니다')
    } catch {
      setToast('분석 실행에 실패했습니다')
    }
    setTimeout(() => setToast(null), 3000)
    setTimeout(() => {
      qc.invalidateQueries({ queryKey: ['projects', agentId] })
      qc.invalidateQueries({ queryKey: ['timeline', agentId] })
    }, 3000)
  }

  return (
    <>
      <button
        onClick={run}
        className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-bold text-primary hover:bg-primary/10"
      >
        <Play size={16} /> 최신 메일 분석
      </button>
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-surface shadow-lg">
          {toast}
        </div>
      )}
    </>
  )
}
