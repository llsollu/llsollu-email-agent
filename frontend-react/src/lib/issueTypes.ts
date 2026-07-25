// 이슈 유형(분야별 추천) 프리셋. 설정 폼과 칸반 라벨 표시에서 공용.
// key = 저장·분석에 쓰이는 식별자, label = 화면 표시명.

export type IssueType = { key: string; label: string }

export const GENERAL: IssueType = { key: 'general', label: '기타' }

// 겹치는 key(general/report/schedule/complaint/bug 등)는 병합 시 앞선 분야의 라벨이 우선.
export const ISSUE_AREAS: { area: string; types: IssueType[] }[] = [
  { area: '개발', types: [
    { key: 'bug', label: '버그' }, { key: 'request', label: '요청' },
    { key: 'question', label: '문의' }, GENERAL ] },
  { area: '영업', types: [
    { key: 'lead', label: '신규 문의' }, { key: 'quote', label: '견적 요청' },
    { key: 'contract', label: '계약·협상' }, { key: 'follow_up', label: '고객 관리' },
    { key: 'complaint', label: '고객 불만' }, GENERAL ] },
  { area: 'PM', types: [
    { key: 'bug', label: '오류' }, { key: 'feature_request', label: '기능 요청' },
    { key: 'status_update', label: '진행 보고' }, { key: 'blocker', label: '결정 필요' },
    { key: 'schedule', label: '일정 조율' }, GENERAL ] },
  { area: '기획', types: [
    { key: 'data_request', label: '자료 요청' }, { key: 'proposal', label: '기획·사업 제안' },
    { key: 'review_request', label: '검토 요청' }, { key: 'meeting', label: '회의 소집' },
    { key: 'report', label: '보고' }, GENERAL ] },
  { area: '경영진', types: [
    { key: 'decision_needed', label: '의사결정·승인' }, { key: 'report', label: '보고' },
    { key: 'external', label: '대외 협력' }, { key: 'schedule', label: '일정 조율' },
    { key: 'escalation', label: '부서 간 이슈' }, GENERAL ] },
  { area: '인사', types: [
    { key: 'recruitment', label: '채용' }, { key: 'leave', label: '휴가·근태' },
    { key: 'payroll', label: '급여' }, { key: 'grievance', label: '고충·불만' },
    { key: 'onboarding_offboarding', label: '입·퇴사' }, GENERAL ] },
  { area: '재무', types: [
    { key: 'expense', label: '경비·지출' }, { key: 'invoice', label: '세금계산서·청구' },
    { key: 'payment_request', label: '대금 지급 요청' }, { key: 'budget', label: '예산' },
    { key: 'audit', label: '감사·증빙' }, GENERAL ] },
  { area: '행정', types: [
    { key: 'facility', label: '시설·비품' }, { key: 'document', label: '서류 발급' },
    { key: 'access', label: '출입·권한' }, GENERAL ] },
]

// 설정이 없을 때의 기본값 = 개발 분야.
export const DEFAULT_ISSUE_TYPES: IssueType[] = ISSUE_AREAS[0].types

/** config.issue_types(및 프리셋 전체)로부터 key→label 맵 생성. 미등록 key 는 호출부에서 key 그대로 노출. */
export function issueLabelMap(configTypes?: IssueType[] | null): Record<string, string> {
  const m: Record<string, string> = {}
  for (const a of ISSUE_AREAS) for (const t of a.types) if (!(t.key in m)) m[t.key] = t.label
  for (const t of configTypes ?? []) if (t?.key) m[t.key] = t.label
  return m
}
