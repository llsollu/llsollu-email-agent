import { useState } from 'react'
import { Info, Plus, Trash2, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { DEFAULT_ISSUE_TYPES, GENERAL, ISSUE_AREAS, type IssueType } from '@/lib/issueTypes'

const AXIS: Record<string, string> = { client: '고객사별', project: '프로젝트별', sender: '발신인별' }

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
  const [categories, setCategories] = useState(String(c.categories ?? ''))
  const [axis, setAxis] = useState(AXIS[String(c.primary_axis ?? 'client')] ? String(c.primary_axis) : 'client')
  const [issueTypes, setIssueTypes] = useState<IssueType[]>(() => ensureGeneral(readIssueTypes(c.issue_types)))
  const [error, setError] = useState<string | null>(null)
  const inp = 'w-full rounded-xl border border-line bg-surface px-3.5 py-2.5 text-sm outline-none focus:border-primary'

  function submit() {
    if (!name.trim()) return setError('이름을 입력하세요')
    setError(null)
    // 대상 메일함은 백엔드에서 항상 본인 메일로 고정하므로 여기서 보내지 않는다.
    onSubmit(name.trim(), { categories: categories.trim(), primary_axis: axis, issue_types: issueTypes })
  }

  const hasKey = (k: string) => issueTypes.some((t) => t.key === k)
  const areaOn = (types: IssueType[]) => types.every((t) => hasKey(t.key))

  function toggleArea(types: IssueType[]) {
    setIssueTypes((prev) => {
      if (types.every((t) => prev.some((p) => p.key === t.key))) {
        // 이미 전부 있으면 제거(단, general 은 항상 유지)
        const keys = new Set(types.filter((t) => t.key !== GENERAL.key).map((t) => t.key))
        return ensureGeneral(prev.filter((p) => !keys.has(p.key)))
      }
      const next = [...prev]
      for (const t of types) if (!next.some((p) => p.key === t.key)) next.push(t)
      return ensureGeneral(next)
    })
  }
  const removeKey = (k: string) =>
    setIssueTypes((prev) => (k === GENERAL.key ? prev : prev.filter((t) => t.key !== k)))

  return (
    <div>
      <div className="mb-3 flex items-center gap-2 rounded-xl bg-primary/10 px-3 py-2.5 text-[13px] font-semibold text-primary">
        <Info size={16} /> 설정은 생성 후에도 언제든 변경할 수 있어요. (추후 변경 가능)
      </div>
      <p className="mb-3 rounded-xl border border-line bg-bg px-3 py-2.5 text-[13px] font-medium text-muted">
        한 번 설정하면 <b>이슈 보드</b>와 <b>타임라인</b> 두 대시보드를 함께 볼 수 있어요. 대상 메일은 항상 <b>본인 메일함</b>이며, 분석·카테고리는 여기서 공유됩니다.
      </p>
      <div className="space-y-3">
        <label className="block"><span className="mb-1 block text-[13px] font-semibold text-muted">이름</span>
          <input className={inp} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="block">
          <span className="mb-1 block text-[13px] font-semibold text-muted">사용자 지정 자동 태그 <span className="font-medium text-muted/70">(선택)</span></span>
          <input className={inp} value={categories} onChange={(e) => setCategories(e.target.value)} placeholder="쉼표로 구분. 예: 제안,계약,개발,납품,유지보수,문의" />
          <span className="mt-1 block text-[12px] font-medium text-muted">비우면 "미지정"만 사용하고, 입력하면 입력한 태그 + "미지정"으로 분류합니다.</span>
        </label>

        <div>
          <div className="text-[15px] font-extrabold">기본 보기 설정</div>
          <p className="mb-2 text-[13px] font-medium text-muted">이슈 카드 제목·타임라인 그룹의 기본 기준</p>
          <div className="inline-flex rounded-xl border border-line p-1">
            {Object.entries(AXIS).map(([k, label]) => (
              <button key={k} onClick={() => setAxis(k)}
                className={cn('rounded-lg px-4 py-1.5 text-sm font-bold', axis === k ? 'bg-primary text-white' : 'text-muted hover:bg-line/50')}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <IssueTypesField
          types={issueTypes}
          areaOn={areaOn}
          onToggleArea={toggleArea}
          onRemove={removeKey}
          onAdd={(t) => setIssueTypes((prev) => (prev.some((p) => p.key === t.key) ? prev : ensureGeneral([...prev, t])))}
        />
      </div>

      {error && <p className="mt-3 text-sm font-semibold text-cancelled">{error}</p>}
      <div className="mt-5 flex items-center">
        {onDelete && <button onClick={onDelete} disabled={busy} className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold text-cancelled hover:bg-cancelled/10"><Trash2 size={16} /> 삭제</button>}
        <button onClick={submit} disabled={busy} className="ml-auto rounded-xl bg-primary px-5 py-2.5 font-bold text-white hover:bg-primary-hover disabled:opacity-50">{submitLabel}</button>
      </div>
    </div>
  )
}

function readIssueTypes(raw: unknown): IssueType[] {
  if (!Array.isArray(raw)) return DEFAULT_ISSUE_TYPES
  const out = raw
    .map((t) => ({ key: String((t as IssueType)?.key ?? '').trim(), label: String((t as IssueType)?.label ?? '').trim() }))
    .filter((t) => t.key && t.label)
  return out.length ? out : DEFAULT_ISSUE_TYPES
}
function ensureGeneral(types: IssueType[]): IssueType[] {
  return types.some((t) => t.key === GENERAL.key) ? types : [...types, GENERAL]
}

function IssueTypesField({
  types, areaOn, onToggleArea, onRemove, onAdd,
}: {
  types: IssueType[]
  areaOn: (t: IssueType[]) => boolean
  onToggleArea: (t: IssueType[]) => void
  onRemove: (key: string) => void
  onAdd: (t: IssueType) => void
}) {
  const [ck, setCk] = useState('')
  const [cl, setCl] = useState('')
  function add() {
    const key = ck.trim(), label = cl.trim()
    if (!key || !label) return
    onAdd({ key, label })
    setCk(''); setCl('')
  }
  return (
    <div>
      <div className="text-[15px] font-extrabold">이슈 분류</div>
      <p className="mb-2 text-[13px] font-medium text-muted">
        분야를 고르면 추천 이슈 유형이 채워집니다. 겸직이면 여러 개 골라도 되고(예: 영업 + PM), 아래에서 빼거나 추가하세요. 분석엔 <b>최종 목록</b>만 쓰입니다.
      </p>

      <div className="mb-1 text-xs font-semibold text-muted">분야별 추천 · 다중 선택 가능</div>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {ISSUE_AREAS.map(({ area, types: at }) => {
          const on = areaOn(at)
          return (
            <button key={area} type="button" onClick={() => onToggleArea(at)}
              className={cn('rounded-lg border px-3 py-1.5 text-[13px] font-bold',
                on ? 'border-primary bg-primary/10 text-primary' : 'border-line text-muted hover:bg-line/50')}>
              {area}
            </button>
          )
        })}
      </div>

      <div className="flex flex-wrap gap-1.5 rounded-xl border border-line bg-bg p-2.5">
        {types.length === 0 ? (
          <span className="text-[13px] font-medium text-muted">분야를 선택하거나 직접 추가하세요</span>
        ) : (
          types.map((t) => (
            <span key={t.key} className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface py-1 pl-2.5 pr-1.5 text-[13px]">
              <b className="font-bold">{t.label}</b>
              <code className="text-[11px] text-muted">{t.key}</code>
              {t.key !== GENERAL.key && (
                <button type="button" aria-label="제거" onClick={() => onRemove(t.key)} className="text-muted hover:text-ink"><X size={13} /></button>
              )}
            </span>
          ))
        )}
      </div>
      <p className="mt-1 text-xs font-medium text-muted">general(기타)은 미분류 대비로 항상 유지됩니다.</p>

      <div className="mt-2 flex gap-2">
        <input value={ck} onChange={(e) => setCk(e.target.value)} placeholder="key (예: renewal)"
          className="w-40 rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
        <input value={cl} onChange={(e) => setCl(e.target.value)} placeholder="표시 이름 (예: 재계약)"
          onKeyDown={(e) => e.key === 'Enter' && add()}
          className="flex-1 rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
        <button type="button" onClick={add} className="flex items-center gap-1 rounded-xl border border-line px-3 py-2 text-sm font-bold text-muted hover:bg-line/50">
          <Plus size={15} /> 추가
        </button>
      </div>
    </div>
  )
}
