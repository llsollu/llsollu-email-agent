# 08. 공통 메일 분석 + 타임라인 에이전트

수신형 에이전트(이슈 관리·타임라인)가 **동일 메일을 중복 분석하지 않도록** 분석을 메일함 단위로 1회만 수행·캐시하고, 그 결과(카테고리 포함)를 에이전트 간 공유한다.

## 구조

- `mail_records` (모델 `MailRecord`): 메일함 단위 공유 저장소. `(mailbox, message_id)` 유일.
  - 원문: subject, from, received_at, **body_text(인용 제거 후 현재 내용만)**
  - 공유 분석: client_name, project_title, **category**, summary, action_required, issue, points, analyzed
- 분석 서비스 `app/services/mail_analysis.py`
  - `strip_quoted`(`mailtext.py`): 인용된 이전 메일/thread 제거 → 현재 메일만 분석
  - `resolve_categories(mailbox)`: 그 메일함을 보는 활성 에이전트들의 `categories` 합집합 → **공유 taxonomy**
  - `analyze_email`: 순수 LLM 분석(드라이런용, 저장 X)
  - `get_or_analyze`: `(mailbox, message_id)` 캐시. 없을 때만 분석·저장
  - `resolve_email`: 트리거 payload/수동/webhook → 이메일 dict

## 에이전트

- **이슈 관리(project_tracker)**: `get_or_analyze` → 공유 분석을 읽어 `projects`/`issues` 갱신. `Project.source_message_id`로 원본 메일 링크.
- **타임라인(mail_timeline)**: `get_or_analyze`로 공유 분석만 보장. 별도 프로젝션 없이 `mail_records`를 조회해 렌더.
- 같은 메일함이면 먼저 실행된 쪽이 분석·저장, 나머지는 캐시 히트 → **분석 1회**.

## API
- `GET /agents/{id}/timeline` — 메일함의 분석 항목(타임라인)
- `GET /agents/{id}/messages/{message_id}` — 원문(기본정보+본문). 칸반 상세/타임라인 모달 공용

## 프론트
- 타임라인 뷰(`view_type: "timeline"`): 고객사/프로젝트 그룹, 카테고리 필터, 검색, 월별 헤더, 카드 펼치기 → 포인트 + 원문 모달
- 칸반 상세 모달 하단에 **원문 메일** 섹션 추가(`SourceEmail` 공용 컴포넌트)

## 마이그레이션
- `mail_records` 테이블 생성(create_all), `projects.source_message_id`(FK→mail_records, ON DELETE SET NULL) 추가.
