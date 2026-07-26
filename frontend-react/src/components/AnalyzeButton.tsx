import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { api } from '@/lib/api'
import type { RunInfo } from '@/lib/types'

/**
 * 이슈 보드·타임라인 공통 "최신 메일 분석" 버튼.
 * 최근 메일을 훑어 아직 분석 안 된 것만 새로 분석·저장(이미 분석된 건 스킵)하여
 * 두 대시보드에 함께 반영한다. 완료되면 새로 분석한 건수를 알려준다.
 */
export function AnalyzeButton({ agentId }: { agentId: string }) {
  const qc = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  function flash(msg: string) {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  async function run() {
    if (busy) return
    setBusy(true)
    setToast('최신 메일을 확인하는 중…')
    try {
      const before = new Set((await api.runs(agentId).catch(() => [])).map((r) => r.id))
      await api.runNow(agentId, false)
      let done: RunInfo | null = null
      for (let i = 0; i < 45; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const runs = await api.runs(agentId).catch(() => [])
        const found = runs.find((r) => r.trigger_source === 'manual' && !before.has(r.id) && r.status !== 'running')
        if (found) { done = found; break }
      }
      qc.invalidateQueries({ queryKey: ['projects', agentId] })
      qc.invalidateQueries({ queryKey: ['timeline', agentId] })
      if (!done) return flash('분석을 계속 진행 중이에요. 잠시 후 새로고침 해주세요.')
      if (done.status === 'error') return flash(`분석 실패: ${done.error ?? '오류'}`)
      const analyzed = Number(done.stats.analyzed ?? 0)
      const scanned = Number(done.stats.processed ?? 0)
      flash(analyzed > 0 ? `새로 ${analyzed}건 분석했어요` : `새로 분석할 메일이 없어요 (최근 ${scanned}건 확인)`)
    } catch {
      flash('분석 실행에 실패했어요')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <button
        onClick={run}
        disabled={busy}
        className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-bold text-primary hover:bg-primary/10 disabled:opacity-50"
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
