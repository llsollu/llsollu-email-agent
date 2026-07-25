import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { X } from 'lucide-react'
import { api } from '@/lib/api'
import type { AgentInfo } from '@/lib/types'
import { MailSchedulerForm } from '@/forms/MailSchedulerForm'
import { ClassifierForm } from '@/forms/ClassifierForm'
import { useEscape } from '@/lib/useEscape'

export function SettingsDialog({ agent, onClose }: { agent: AgentInfo; onClose: () => void }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmDel, setConfirmDel] = useState(false)
  useEscape(() => (confirmDel ? setConfirmDel(false) : onClose()))

  async function save(name: string, config: Record<string, unknown>) {
    setBusy(true)
    setError(null)
    try {
      await api.updateAgent(agent.id, { name, config })
      await qc.invalidateQueries({ queryKey: ['agents'] })
      qc.invalidateQueries({ queryKey: ['projects', agent.id] })
      qc.invalidateQueries({ queryKey: ['runs', agent.id] })
      qc.invalidateQueries({ queryKey: ['schedule', agent.id] })
      qc.invalidateQueries({ queryKey: ['timeline', agent.id] })
      onClose()
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  async function del() {
    setBusy(true)
    try {
      await api.deleteAgent(agent.id)
      await qc.invalidateQueries({ queryKey: ['agents'] })
      onClose()
      navigate('/')
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  const isSched = agent.template_key === 'mail_scheduler'
  const isClassifier = agent.template_key === 'project_tracker'

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-6" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-[600px] overflow-y-auto rounded-2xl border border-line bg-surface p-6 shadow-[var(--shadow)]" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-extrabold">에이전트 설정</h2>
          <button aria-label="닫기" onClick={onClose} className="text-muted hover:text-ink"><X size={20} /></button>
        </div>

        {isSched && (
          <MailSchedulerForm
            initialName={agent.name} initialConfig={agent.config} wizard={false}
            busy={busy} submitLabel="저장" onSubmit={save} onDelete={() => setConfirmDel(true)}
          />
        )}
        {isClassifier && (
          <ClassifierForm
            initialName={agent.name} initialConfig={agent.config}
            busy={busy} submitLabel="저장" onSubmit={save} onDelete={() => setConfirmDel(true)}
          />
        )}
        {!isSched && !isClassifier && <p className="text-sm text-muted">이 템플릿은 아직 편집 폼이 없습니다.</p>}

        {error && <p className="mt-3 text-sm font-semibold text-cancelled">{error}</p>}
      </div>

      {confirmDel && (
        <div className="fixed inset-0 z-[60] grid place-items-center bg-black/40 p-6" onClick={() => setConfirmDel(false)}>
          <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-6 shadow-[var(--shadow)]" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-base font-extrabold">삭제</h3>
            <p className="mt-2 text-sm font-medium text-muted">"{agent.name}" 을(를) 삭제할까요?</p>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setConfirmDel(false)} className="rounded-xl px-4 py-2 font-semibold text-muted hover:bg-line/50">취소</button>
              <button onClick={del} disabled={busy} className="rounded-xl bg-cancelled px-4 py-2 font-bold text-white disabled:opacity-50">삭제</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
