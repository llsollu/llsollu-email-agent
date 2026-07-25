import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

/** 메일 본문을 사람이 읽기 좋은 텍스트로 정리. HTML 이면 태그/스타일 제거 + 블록 단위 줄바꿈. */
function readableBody(raw?: string | null): string {
  if (!raw) return ''
  if (!/[<&]/.test(raw)) return raw.trim() // 평문
  const doc = new DOMParser().parseFromString(raw, 'text/html')
  doc.querySelectorAll('style, script, head, title, meta, link, noscript').forEach((el) => el.remove())
  doc.querySelectorAll('br').forEach((el) => el.replaceWith('\n'))
  doc.querySelectorAll('p, div, tr, li, h1, h2, h3, h4, h5, blockquote, table, section, article, header, footer')
    .forEach((el) => el.append('\n'))
  const text = (doc.body?.textContent ?? '')
    .replace(/ /g, ' ')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
  return text || raw.trim()
}

function fmtKst(iso?: string | null) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (isNaN(+d)) return String(iso)
  const k = new Date(d.getTime() + 9 * 3600 * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${k.getUTCFullYear()}-${p(k.getUTCMonth() + 1)}-${p(k.getUTCDate())} ${p(k.getUTCHours())}:${p(k.getUTCMinutes())}`
}

/** 원문 메일: 기본 정보 + 본문. 칸반 상세/타임라인 모달에서 공용. */
export function SourceEmail({ agentId, messageId }: { agentId: string; messageId: string }) {
  const q = useQuery({
    queryKey: ['message', agentId, messageId],
    queryFn: () => api.message(agentId, messageId),
  })
  const body = useMemo(() => readableBody(q.data?.body_text), [q.data?.body_text])

  return (
    <div className="mt-4 rounded-xl border border-line bg-bg p-3">
      <div className="mb-2 text-[13px] font-extrabold text-muted">원본 메일</div>
      {q.isLoading && <p className="text-sm text-muted">불러오는 중…</p>}
      {q.isError && <p className="text-sm font-semibold text-cancelled">원문을 불러오지 못했습니다</p>}
      {q.data && (
        <>
          <dl className="grid grid-cols-[64px_1fr] gap-x-3 gap-y-1 text-[13px]">
            <dt className="font-semibold text-muted">발신</dt>
            <dd className="font-medium">{q.data.from_name ? `${q.data.from_name} · ` : ''}{q.data.from_address || '-'}</dd>
            <dt className="font-semibold text-muted">수신</dt>
            <dd className="font-medium">{fmtKst(q.data.received_at)}</dd>
            <dt className="font-semibold text-muted">제목</dt>
            <dd className="font-medium">{q.data.subject || '-'}</dd>
          </dl>
          <div className="mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-surface p-2.5 text-[13px] leading-relaxed">
            {body || '(본문 없음)'}
          </div>
          <p className="mt-1.5 text-xs font-medium text-muted">※ 인용된 이전 메일은 분석·표시에서 제외됩니다(현재 메일 내용만).</p>
        </>
      )}
    </div>
  )
}
