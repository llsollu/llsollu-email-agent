import { useEffect, useRef, useState } from 'react'
import { Info, RefreshCw, Send, Trash2, X } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/store/auth'
import {
  WEEKDAY_NAMES, cronFromScheduleUi, humanFromScheduleUi, scheduleUiFromCron, type ScheduleUi,
} from '@/lib/schedule'
import { cn } from '@/lib/utils'

const SPECIAL_CHIPS: Record<string, string> = { '오늘 날짜': '오늘', '이번 달 데이터': '이번달', '이번 달(월)': '월' }
const SPECIAL_TOKENS = new Set(['오늘', 'today', '날짜', '이번달', '현재월', '이달', '이번달데이터', '월', '이번달월', '현재월숫자'])

type Props = {
  initialName: string
  initialConfig: Record<string, unknown>
  wizard?: boolean
  busy?: boolean
  submitLabel?: string
  onSubmit: (name: string, config: Record<string, unknown>) => void
  onDelete?: () => void
}

export function MailSchedulerForm({
  initialName, initialConfig: c, wizard = true, busy = false, submitLabel = '생성', onSubmit, onDelete,
}: Props) {
  const senderEmail = useAuth((s) => s.user?.email ?? '')
  const [name, setName] = useState(initialName)
  const [fileUrl, setFileUrl] = useState(String(c.sharepoint_file_url ?? ''))
  const [recipient, setRecipient] = useState(String(c.recipient_email ?? ''))
  const [cc, setCc] = useState(String(c.cc_email ?? ''))
  const [subject, setSubject] = useState(String(c.subject_template ?? ''))
  const [body, setBody] = useState(String(c.body_template ?? ''))
  const [dateColumn, setDateColumn] = useState(String(c.date_column ?? ''))
  const [schedule, setSchedule] = useState<ScheduleUi>(
    (c.schedule_ui as ScheduleUi) || scheduleUiFromCron(String(c.cron ?? '')) || { kind: 'daily', hour: 9, minute: 0 },
  )
  const [columns, setColumns] = useState<string[]>([])
  const [loadingCols, setLoadingCols] = useState(false)
  const [colsError, setColsError] = useState<string | null>(null)
  const [step, setStep] = useState(0)
  const [stepError, setStepError] = useState<string | null>(null)
  const [dataError, setDataError] = useState<string | null>(null)

  const subjectRef = useRef<HTMLInputElement>(null)
  const bodyRef = useRef<HTMLTextAreaElement>(null)
  const lastFocused = useRef<'subject' | 'body'>('body')

  useEffect(() => {
    if (!wizard && fileUrl.trim()) void loadColumns()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function loadColumns() {
    if (!fileUrl.trim()) return
    setLoadingCols(true)
    setColsError(null)
    try {
      const res = await api.mailSchedulerColumns(fileUrl.trim())
      setColumns(res.columns)
    } catch (e) {
      setColsError((e as Error).message)
    } finally {
      setLoadingCols(false)
    }
  }

  // 참조 파일 URL 은 선택. 이름·수신자만 필수.
  const step1Valid = name.trim() && recipient.trim()

  function tokenError(label: string, text: string): string | null {
    if (!text.includes('{')) return null
    const re = /\{\{\s*([^{}]*?)\s*\}\}/g
    const names = [...text.matchAll(re)].map((m) => m[1].trim())
    const stripped = text.replace(re, '')
    if (stripped.includes('{') || stripped.includes('}')) return `${label}의 {{ }} 형식이 올바르지 않습니다`
    for (const nm of names) {
      if (!nm) return `${label}에 빈 데이터 태그({{}})가 있습니다`
      if (columns.length && !SPECIAL_TOKENS.has(nm) && !columns.includes(nm))
        return `${label}에 사용할 수 없는 데이터명이 있습니다: "${nm}"`
    }
    return null
  }

  function buildConfig(): Record<string, unknown> {
    return {
      sharepoint_file_url: fileUrl.trim(),
      mail_sender: senderEmail,
      recipient_email: recipient.trim(),
      cc_email: cc.trim(),
      alert_email: senderEmail,
      date_column: dateColumn,
      subject_template: subject,
      body_template: body,
      schedule_ui: schedule,
      cron: cronFromScheduleUi(schedule),
    }
  }

  function submit() {
    if (!step1Valid) return setDataError('이름·수신자 이메일을 입력하세요')
    const err = tokenError('메일 제목', subject) ?? tokenError('메일 작성 내용', body)
    if (err) return setDataError(err)
    setDataError(null)
    onSubmit(name.trim(), buildConfig())
  }

  async function goStep2() {
    if (!step1Valid) return setStepError('이름·수신자 이메일을 입력하세요')
    setStepError(null)
    await loadColumns()
    setStep(1)
  }

  function insert(field: 'subject' | 'body', token: string, at?: number) {
    const el = field === 'subject' ? subjectRef.current : bodyRef.current
    const val = field === 'subject' ? subject : body
    const set = field === 'subject' ? setSubject : setBody
    const start = at ?? el?.selectionStart ?? val.length
    const end = at ?? el?.selectionEnd ?? val.length
    const next = val.slice(0, start) + token + val.slice(end)
    set(next)
    requestAnimationFrame(() => {
      el?.focus()
      const pos = start + token.length
      el?.setSelectionRange(pos, pos)
    })
  }

  // ── 렌더 헬퍼 ──
  const note = (
    <div className="mb-3 flex items-center gap-2 rounded-xl bg-primary/10 px-3 py-2.5 text-[13px] font-semibold text-primary">
      <Info size={16} /> 설정은 생성 후에도 언제든 변경할 수 있어요. (추후 변경 가능)
    </div>
  )

  const basicFields = (
    <div className="space-y-2">
      <Field label="이름"><input className={inp} value={name} onChange={(e) => setName(e.target.value)} placeholder="예: 세금계산서 발행 알림" /></Field>
      <Field label="참조 파일 URL (엑셀 표 형식, 선택)"><input className={inp} value={fileUrl} onChange={(e) => setFileUrl(e.target.value)} placeholder="SharePoint 공유 xlsx 링크 (없으면 데이터 없이 발송)" /></Field>
      <Field label="수신자 이메일 (쉼표로 여러 명)"><input className={inp} value={recipient} onChange={(e) => setRecipient(e.target.value)} placeholder="a@llsollu.com, b@llsollu.com" /></Field>
      <Field label="참조 이메일 (쉼표로 여러 명, 선택)"><input className={inp} value={cc} onChange={(e) => setCc(e.target.value)} placeholder="cc@llsollu.com" /></Field>
      <div className="flex items-center gap-1.5 pt-1 text-[13px] font-medium text-muted">
        <Send size={15} /> 발신 계정: {senderEmail || '본인 계정'} (본인 계정으로 발송)
      </div>
    </div>
  )

  const dataSection = (
    <div>
      <div className="flex items-center gap-2">
        <span className="text-[15px] font-extrabold">사용 가능한 데이터</span>
        <button onClick={loadColumns} disabled={loadingCols} aria-label="컬럼 다시 불러오기" className="text-muted hover:text-ink"><RefreshCw size={16} /></button>
      </div>
      <p className="text-[13px] font-medium text-muted">아래 항목을 드래그(또는 탭)해서 발송기준일·제목·본문에 넣으세요</p>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {Object.entries(SPECIAL_CHIPS).map(([label, token]) => (
          <Chip key={token} token={token} label={label} special onClick={() => insert(lastFocused.current, `{{${token}}}`)} />
        ))}
      </div>
      <p className="mt-1 text-xs font-medium text-muted">· "이번 달 데이터"는 발송월에 해당하는 월 컬럼(예: 7월이면 "7월") 값이 들어갑니다</p>

      <div className="mt-2.5">
        {loadingCols ? <p className="text-sm text-muted">불러오는 중…</p>
          : colsError ? <p className="text-sm font-semibold text-cancelled">{colsError}</p>
          : columns.length === 0 ? <p className="text-sm font-medium text-muted">컬럼이 없습니다. 참조 파일 URL을 확인하세요.</p>
          : <div className="flex flex-wrap gap-1.5">{columns.map((col) => (
              <Chip key={col} token={col} label={col} onClick={() => insert(lastFocused.current, `{{${col}}}`)} />
            ))}</div>}
      </div>

      <Hr />
      <Label>발송기준일(발송 규칙 데이터)</Label>
      <DateDrop value={dateColumn} columns={columns} onSet={setDateColumn} onClear={() => setDateColumn('')} />
      <p className="mt-1 text-[13px] font-medium text-muted">입력하지 않으면 규칙 확인 주기마다 발송</p>

      <div className="mt-5"><Label>규칙 확인 주기</Label>
        <ScheduleBuilder value={schedule} onChange={setSchedule} />
      </div>

      <div className="mt-5"><Label>메일 제목(드래그로 데이터 삽입 가능)</Label>
        <input
          ref={subjectRef} className={inp} value={subject}
          onFocus={() => (lastFocused.current = 'subject')}
          onChange={(e) => setSubject(e.target.value)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); insert('subject', `{{${e.dataTransfer.getData('text/plain')}}}`, e.currentTarget.selectionStart ?? undefined) }}
          placeholder="예: [{{거래처}}] 발행 요청"
        />
      </div>

      <div className="mt-4"><Label>메일 작성 내용</Label>
        <textarea
          ref={bodyRef} className={cn(inp, 'min-h-40 resize-y')} value={body}
          onFocus={() => (lastFocused.current = 'body')}
          onChange={(e) => setBody(e.target.value)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); insert('body', `{{${e.dataTransfer.getData('text/plain')}}}`, e.currentTarget.selectionStart ?? undefined) }}
          placeholder={'본문을 작성하고, 원하는 위치에 데이터를 드래그해 넣으세요.\n예: 안녕하세요, {{거래처}} 담당자님'}
        />
      </div>
    </div>
  )

  if (!wizard) {
    return (
      <div>
        {note}
        {basicFields}
        <Hr />
        {dataSection}
        {dataError && <p className="mt-2.5 text-sm font-semibold text-cancelled">{dataError}</p>}
        <div className="mt-4 flex items-center">
          {onDelete && <button onClick={onDelete} disabled={busy} className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold text-cancelled hover:bg-cancelled/10"><Trash2 size={16} /> 삭제</button>}
          <button onClick={submit} disabled={busy} className={cn(primaryBtn, 'ml-auto')}>{submitLabel}</button>
        </div>
      </div>
    )
  }

  return step === 0 ? (
    <div>
      <StepBadge step={1} title="기본 정보" />
      {note}
      {basicFields}
      {stepError && <p className="mt-2 text-sm font-semibold text-cancelled">{stepError}</p>}
      <button onClick={goStep2} disabled={busy || loadingCols} className={cn(primaryBtn, 'mt-5')}>{loadingCols ? '불러오는 중…' : '다음'}</button>
    </div>
  ) : (
    <div>
      <StepBadge step={2} title="데이터 · 주기 · 본문" />
      {dataSection}
      {dataError && <p className="mt-2.5 text-sm font-semibold text-cancelled">{dataError}</p>}
      <div className="mt-5 flex items-center">
        <button onClick={() => setStep(0)} className="rounded-xl px-3 py-2 font-semibold text-muted hover:bg-line/50">이전</button>
        <button onClick={submit} disabled={busy} className={cn(primaryBtn, 'ml-auto')}>{busy ? '처리 중…' : submitLabel}</button>
      </div>
    </div>
  )
}

const inp = 'w-full rounded-xl border border-line bg-surface px-3.5 py-2.5 text-sm outline-none focus:border-primary'
const primaryBtn = 'rounded-xl bg-primary px-5 py-2.5 font-bold text-white hover:bg-primary-hover disabled:opacity-50'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-1 block text-[13px] font-semibold text-muted">{label}</span>{children}</label>
}
function Label({ children }: { children: React.ReactNode }) { return <div className="mb-1.5 text-[15px] font-extrabold">{children}</div> }
function Hr() { return <div className="my-6 border-t border-line" /> }

function Chip({ token, label, special, onClick }: { token: string; label: string; special?: boolean; onClick: () => void }) {
  return (
    <button
      draggable
      onDragStart={(e) => e.dataTransfer.setData('text/plain', token)}
      onClick={onClick}
      className={cn('cursor-grab rounded-lg px-2.5 py-1 text-xs font-bold active:cursor-grabbing',
        special ? 'bg-amber/20 text-[#8a5a00]' : 'bg-primary/10 text-primary')}
    >
      {label}
    </button>
  )
}

function DateDrop({ value, columns, onSet, onClear }: { value: string; columns: string[]; onSet: (v: string) => void; onClear: () => void }) {
  return (
    <div
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => { e.preventDefault(); onSet(e.dataTransfer.getData('text/plain')) }}
      className="flex items-center gap-2 rounded-xl border border-dashed border-line px-3 py-2.5"
    >
      {value ? (
        <span className="flex items-center gap-1.5 rounded-lg bg-primary/10 px-2.5 py-1 text-xs font-bold text-primary">
          {value}<button onClick={onClear} aria-label="지우기"><X size={14} /></button>
        </span>
      ) : (
        <span className="text-sm font-medium text-muted">드래그해서 입력</span>
      )}
      {columns.length > 0 && (
        <select value={value} onChange={(e) => onSet(e.target.value)} className="ml-auto rounded-lg border border-line bg-surface px-2 py-1 text-sm outline-none">
          <option value="">(선택)</option>
          {columns.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      )}
    </div>
  )
}

function ScheduleBuilder({ value, onChange }: { value: ScheduleUi; onChange: (s: ScheduleUi) => void }) {
  const kind = value.kind ?? 'daily'
  const set = (patch: Partial<ScheduleUi>) => onChange({ ...value, ...patch })
  const sel = 'rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm outline-none focus:border-primary'
  const num = (from: number, to: number) => Array.from({ length: to - from + 1 }, (_, i) => from + i)
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <select value={kind} onChange={(e) => set({ kind: e.target.value })} className={sel}>
          <option value="daily">매일</option><option value="weekly">매주</option><option value="monthly">매월</option>
          <option value="hourly">매시간</option><option value="minutely">분마다</option>
        </select>
        {kind === 'weekly' && (
          <select value={value.weekday ?? 1} onChange={(e) => set({ weekday: +e.target.value })} className={sel}>
            {num(1, 7).map((i) => <option key={i} value={i}>{WEEKDAY_NAMES[i - 1]}요일</option>)}
          </select>
        )}
        {kind === 'monthly' && (
          <select value={value.day ?? 1} onChange={(e) => set({ day: +e.target.value })} className={sel}>
            {num(1, 31).map((i) => <option key={i} value={i}>{i}일</option>)}
          </select>
        )}
        {(kind === 'daily' || kind === 'weekly' || kind === 'monthly') && (
          <>
            <select value={value.hour ?? 9} onChange={(e) => set({ hour: +e.target.value })} className={sel}>
              {num(0, 23).map((i) => <option key={i} value={i}>{String(i).padStart(2, '0')}시</option>)}
            </select>
            <select value={value.minute ?? 0} onChange={(e) => set({ minute: +e.target.value })} className={sel}>
              {num(0, 59).map((i) => <option key={i} value={i}>{String(i).padStart(2, '0')}분</option>)}
            </select>
          </>
        )}
        {kind === 'hourly' && (
          <select value={value.minute ?? 0} onChange={(e) => set({ minute: +e.target.value })} className={sel}>
            {num(0, 59).map((i) => <option key={i} value={i}>매시 {String(i).padStart(2, '0')}분</option>)}
          </select>
        )}
        {kind === 'minutely' && (
          <select value={value.interval ?? 30} onChange={(e) => set({ interval: +e.target.value })} className={sel}>
            {[5, 10, 15, 20, 30, 60].map((i) => <option key={i} value={i}>{i}분마다</option>)}
          </select>
        )}
      </div>
      <p className="mt-1.5 text-[13px] font-bold text-primary">→ {humanFromScheduleUi(value)}</p>
    </div>
  )
}

function StepBadge({ step, title }: { step: number; title: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <span className="grid h-7 w-7 place-items-center rounded-full bg-primary text-sm font-bold text-white">{step}</span>
      <span className="text-base font-extrabold">{title}</span>
      <span className="text-sm font-semibold text-muted">({step}/2)</span>
    </div>
  )
}
