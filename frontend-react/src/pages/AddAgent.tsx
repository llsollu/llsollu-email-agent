import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, ChevronLeft } from 'lucide-react'
import { api } from '@/lib/api'
import type { TemplateInfo } from '@/lib/types'
import { useAgents } from '@/hooks/useAgents'
import { MailSchedulerForm } from '@/forms/MailSchedulerForm'
import { ClassifierForm } from '@/forms/ClassifierForm'
import { AgentIcon } from '@/components/AgentIcon'

// 하나만 만들 수 있는 템플릿(메일 분석·요약 관리).
const SINGLETON_TEMPLATES = new Set(['project_tracker'])

function cnCard(taken: boolean) {
  return [
    'flex h-[210px] w-[290px] flex-col rounded-2xl border p-5 text-left transition',
    taken ? 'cursor-not-allowed border-line bg-surface opacity-55' : 'border-line bg-surface hover:border-primary',
  ].join(' ')
}

export function AddAgent() {
  const templates = useQuery({ queryKey: ['templates'], queryFn: api.templates })
  const agents = useAgents()
  const [picked, setPicked] = useState<TemplateInfo | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const qc = useQueryClient()

  const existingKeys = new Set((agents.data ?? []).map((a) => a.template_key))

  async function create(name: string, config: Record<string, unknown>) {
    setBusy(true)
    setError(null)
    try {
      const agent = await api.createAgent(picked!.key, name, config)
      await qc.invalidateQueries({ queryKey: ['agents'] })
      navigate(`/agents/${agent.id}`)
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-[640px] p-7">
        {!picked ? (
          <>
            <h1 className="text-2xl font-extrabold tracking-tight">어떤 에이전트를 만들까요?</h1>
            <p className="mt-1 text-sm font-medium text-muted">템플릿을 선택하면 설정 단계로 넘어갑니다</p>
            {templates.isLoading && <p className="mt-6 text-sm text-muted">템플릿을 불러오는 중…</p>}
            {templates.isError && <p className="mt-6 text-sm font-semibold text-cancelled">템플릿을 불러오지 못했습니다</p>}
            <div className="mt-6 flex flex-wrap gap-4">
              {templates.data?.map((t) => {
                const taken = SINGLETON_TEMPLATES.has(t.key) && existingKeys.has(t.key)
                return (
                  <button key={t.key} onClick={() => !taken && setPicked(t)} disabled={taken}
                    className={cnCard(taken)}>
                    <div className="grid h-[52px] w-[52px] place-items-center rounded-[14px] bg-gradient-to-br from-primary to-brand2 text-white">
                      <AgentIcon viewType={t.view_type} size={26} />
                    </div>
                    <div className="mt-4 flex items-center gap-2 text-base font-bold">
                      {t.name}
                      {taken && <span className="rounded-full bg-line px-2 py-0.5 text-[11px] font-bold text-muted">이미 생성됨</span>}
                    </div>
                    <p className="mt-2 line-clamp-3 flex-1 text-[13px] font-medium text-muted">{t.description}</p>
                    <div className="flex items-center justify-between text-xs font-bold text-primary">
                      <span>{t.trigger_kind === 'schedule' ? '스케줄형' : '메일 수신형'}</span>
                      {taken ? <span className="text-muted">하나만 생성 가능</span> : <ArrowRight size={16} />}
                    </div>
                  </button>
                )
              })}
            </div>
          </>
        ) : (
          <>
            <button onClick={() => setPicked(null)} className="mb-4 flex items-center gap-1 text-sm font-semibold text-muted hover:text-ink">
              <ChevronLeft size={16} /> 템플릿 다시 선택
            </button>
            {picked.key === 'mail_scheduler' ? (
              <MailSchedulerForm initialName={picked.name} initialConfig={{}} wizard busy={busy} submitLabel="생성" onSubmit={create} />
            ) : (
              <ClassifierForm initialName={picked.name} initialConfig={{}} busy={busy} submitLabel="생성" onSubmit={create} />
            )}
            {error && <p className="mt-3 text-sm font-semibold text-cancelled">생성 실패: {error}</p>}
          </>
        )}
      </div>
    </div>
  )
}
