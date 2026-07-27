# 08. 공통 메일 분석 + 타임라인 에이전트

수신형 에이전트(이슈 관리·타임라인)가 **동일 메일을 중복 분석하지 않도록** 분석을 메일함 단위로 1회만 수행·캐시하고, 그 결과(카테고리 포함)를 에이전트 간 공유한다.

## 구조

- `mail_records` (모델 `MailRecord`): 메일함 단위 공유 저장소. `(mailbox, message_id)` 유일.
  - 원문: subject, from_address/from_name, **to_recipients/cc_recipients(전체 내역)**, received_at, **body_text(인용 제거 후 현재 내용만)**
  - 공유 분석: client_name, project_title, **category**, summary, action_required, issue, points, **keywords(핵심+유사어)**, **recipient_role(to=직접수신/cc=참조/other, 메일함=본인 주소 기준)**, analyzed, analyzer_version
- 분석 서비스 `app/services/mail_analysis.py`
  - `strip_quoted`(`mailtext.py`): 인용된 이전 메일/thread 제거 → 현재 메일만 분석
  - `resolve_categories(mailbox)`: 그 메일함 활성 에이전트들의 `categories`(사용자 지정 자동 태그) 합집합 **+ 항상 "미지정"** → 공유 taxonomy(설정 없으면 `["미지정"]`)
  - `resolve_issue_types(mailbox)`: 이슈 유형(분야별 추천으로 커스터마이즈) 합집합 → 분석 프롬프트에 주입(기본=개발 분야)
  - `analyze_email`: 순수 LLM 분석(드라이런용, 저장 X). `(결과, 토큰 사용량)` 반환
  - `get_or_analyze`: `(mailbox, message_id)` 캐시. 없을 때만 분석·저장. `agent_id/run_id` 주면 `llm_jobs`에 사용량 적재
  - `resolve_email`: 트리거 payload/수동/webhook → 이메일 dict

## 뷰 (한 에이전트, 두 뷰)

**타임라인은 별도 템플릿이 아니라 `project_tracker` 에이전트의 두 번째 뷰**다(`ViewSpec.views`: `board`=kanban, `timeline`). 등록 템플릿은 `project_tracker`·`mail_scheduler` 2종뿐.

- **이슈 보드(kanban)**: `get_or_analyze` → 공유 분석을 읽어 카드 업서트. **메일 1건 = 카드 1개**(`Project.source_message_id` 기준 멱등; 같은 스레드/유형도 메일마다 별도 카드). 고객사만 식별돼도 카드 생성(프로젝트 미상은 "(미지정)").
- **타임라인**: 별도 프로젝션 없이 `mail_records`를 커서 페이지네이션으로 조회해 렌더(직접수신/참조·카테고리·이슈 유형 표시, 발신인/고객사/프로젝트 그룹).
- 두 뷰가 같은 메일함 분석을 공유 → **분석 1회**(캐시 히트). "최신 메일 분석" 버튼은 최근 N건 중 미분석분만 일괄 처리.

## API
- `GET /agents/{id}/timeline` — 메일함의 분석 항목(타임라인)
- `GET /agents/{id}/messages/{message_id}` — 원문(기본정보+본문). 칸반 상세/타임라인 모달 공용

## 프론트
- 타임라인 뷰(`view_type: "timeline"`): 고객사/프로젝트 그룹, 카테고리 필터, 검색, 월별 헤더, 카드 펼치기 → 포인트 + 원문 모달
- 칸반 상세 모달 하단에 **원문 메일** 섹션 추가(`SourceEmail` 공용 컴포넌트)

## 마이그레이션
- `mail_records` 테이블 생성(create_all), `projects.source_message_id`(FK→mail_records, ON DELETE SET NULL) 추가.
- 이후 psql 수동 `ALTER TABLE`로 추가된 컬럼: `mail_records`·`projects`에 `keywords`, `mail_records`에 `to_recipients`/`cc_recipients`/`recipient_role`, `projects`에 `from_name`/`from_address`/`recipient_role`/`archived_at`. (Alembic 미사용)
