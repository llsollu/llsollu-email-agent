import { useState } from 'react'
import { Info, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'

const CARD_TITLE: Record<string, string> = { client: '고객사', category: '분류', title: '요약 제목' }

type Props = {
  initialName: string
  initialConfig: Record<string, unknown>
  busy?: boolean
  submitLabel?: string
  onSubmit: (name: string, config: Record<string, unknown>) => void
  onDelete?: () => void
}

export function ClassifierForm({ initialName, initialConfig: c, busy = false, submitLabel = '생성', onSubmit, onDelete }: Props) {
  const [name, setName] = useState(initialName)
  const [mailbox, setMailbox] = useState(String(c.mailbox ?? ''))
  const [categories, setCategories] = useState(String(c.categories ?? ''))
  const [cardTitle, setCardTitle] = useState(CARD_TITLE[String(c.card_title_field ?? 'client')] ? String(c.card_title_field) : 'client')
  const [error, setError] = useState<string | null>(null)

  const inp = 'w-full rounded-xl border border-line bg-surface px-3.5 py-2.5 text-sm outline-none focus:border-primary'

  function submit() {
    if (!name.trim() || !mailbox.trim()) return setError('이름·대상 메일함을 입력하세요')
    setError(null)
    onSubmit(name.trim(), { mailbox: mailbox.trim(), categories: categories.trim(), card_title_field: cardTitle })
  }

  return (
    <div>
      <div className="mb-3 flex items-center gap-2 rounded-xl bg-primary/10 px-3 py-2.5 text-[13px] font-semibold text-primary">
        <Info size={16} /> 설정은 생성 후에도 언제든 변경할 수 있어요. (추후 변경 가능)
      </div>
      <div className="space-y-3">
        <label className="block"><span className="mb-1 block text-[13px] font-semibold text-muted">이름</span>
          <input className={inp} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="block"><span className="mb-1 block text-[13px] font-semibold text-muted">대상 메일함</span>
          <input className={inp} value={mailbox} onChange={(e) => setMailbox(e.target.value)} placeholder="분류할 메일을 수신하는 회사 메일 주소" /></label>
        <label className="block"><span className="mb-1 block text-[13px] font-semibold text-muted">메일 분류 카테고리</span>
          <input className={inp} value={categories} onChange={(e) => setCategories(e.target.value)} placeholder="쉼표로 구분. 예: 제안,계약,개발,납품,유지보수,문의" /></label>

        <div>
          <div className="text-[15px] font-extrabold">요약 카드 타이틀</div>
          <p className="mb-2 text-[13px] font-medium text-muted">칸반 카드에 크게 표시할 항목을 고르세요</p>
          <div className="inline-flex rounded-xl border border-line p-1">
            {Object.entries(CARD_TITLE).map(([k, label]) => (
              <button key={k} onClick={() => setCardTitle(k)}
                className={cn('rounded-lg px-4 py-1.5 text-sm font-bold', cardTitle === k ? 'bg-primary text-white' : 'text-muted hover:bg-line/50')}>
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <p className="mt-3 text-sm font-semibold text-cancelled">{error}</p>}
      <div className="mt-5 flex items-center">
        {onDelete && <button onClick={onDelete} disabled={busy} className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold text-cancelled hover:bg-cancelled/10"><Trash2 size={16} /> 삭제</button>}
        <button onClick={submit} disabled={busy} className="ml-auto rounded-xl bg-primary px-5 py-2.5 font-bold text-white hover:bg-primary-hover disabled:opacity-50">{submitLabel}</button>
      </div>
    </div>
  )
}
