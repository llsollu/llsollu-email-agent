# 09. 세션 인수인계 (크리티컬 메모)

코드로 알 수 있는 건 생략. **재분석으로 놓치기 쉽거나 틀리기 쉬운 것**만.
상세는 [07](07-react-tauri-migration.md)(프론트 전환), [08](08-shared-analysis-and-timeline.md)(공유 분석·타임라인) 참고.
docs **03·05·06·08은 현행 반영**됨. **02(백엔드 에이전트 프레임워크)는 유효**. **01·04는 구(舊) Flutter 기준이라 프론트 서술이 outdated**(각 문서 상단 배너 참고).
아래 "이번 세션 반영(현재 상태 요약)" 섹션이 최신 기능 전반을 요약한다.

## 스택 현황 (중요)
- 프론트는 **`frontend-react/`(React+Vite+TS, Tauri)** 로 전환 완료. **`frontend/`(Flutter) 삭제됨.**
- FastAPI가 `:8000`에서 `frontend-react/dist`(바인드 마운트)를 SPA로 서빙(동일 오리진). `deploy/docker-compose.yml` 참고.

## 환경 함정
- **Node는 nvm으로만** 존재. 명령 전 반드시:
  `export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"` (node v24, `~/.nvm/versions/node/v24.18.0/bin`).
- **무암호 sudo 없음.** 시스템 패키지 설치 불가.
- **Tauri 데스크톱 빌드는 이 리눅스 호스트에서 불가**(webkit2gtk 없음/ sudo 없음). 웹은 완전 동작. 데스크톱 빌드는 Windows(WebView2)/CI에서.
- 이 호스트는 `10.0.0.x` 망 → 사내 `192.168.x`(예: 옛 LLM `192.168.10.30`)에 **도달 불가**.

## 배포/빌드 (실서비스 미운영 — 바로 반영 OK)
- 백엔드 변경 반영:
  `docker compose -f deploy/docker-compose.yml build api worker && docker compose -f deploy/docker-compose.yml up -d --force-recreate api worker`
- 프론트 반영: `cd frontend-react && npm run build` → dist가 바인드 마운트라 자동 서빙(브라우저 강력 새로고침).
- **DB 마이그레이션 도구 없음(Alembic X).** 새 테이블은 `docker exec deploy-api-1 python -m app.tools.init_db`(create_all, 누락 테이블만 생성). **컬럼 추가/변경은 psql로 수동 `ALTER TABLE`.** postgres 데이터는 볼륨에 영속.

## 외부 연동
- **LLM**: OpenAI 호환, `backend/.env`의 `LLM_BASE_URL=http://211.236.232.30:20080/v1` (모델 gemma). 사내 IP 대신 이 주소 사용.
- **MS Graph**: 앱 자격증명에 **디렉터리 읽기(User.Read.All) 없음.** 사내 계정 확인은 `/users/{email}/mailFolders/Inbox` 접근(200/404)으로 판별(= `graph_client.find_user`). `/users` 직접 조회는 403.
- 요청은 **IP 화이트리스트 미들웨어**로 사내망 제한(로컬호스트 허용).

## 인증 (함정 주의)
- 웹 = **httpOnly 세션 쿠키(JWT)**, 데스크톱(Tauri) = **`Authorization: Bearer`**(login/register 응답의 `access_token`). `get_current_user`가 둘 다 허용.
- `check-email`: 비번 있는 계정→`existing`(로그인), DB에 없고 사내계정→`needs_setup`(비번 설정), 그 외→`not_company`.
- **`users.password_hash`를 NULL로 두지 말 것** — 로그인도 설정창도 아닌 상태 유발 가능(과거 버그).
- **관리자**: `users.is_admin`(+`is_active`). `ADMIN_EMAILS` env(`backend/.env`, 현재 `sh.cho@llsollu.com`)로 부트스트랩, `is_effective_admin`=DB플래그 or env. `/admin/*`는 `get_admin_user`(403), 비활성 계정은 로그인 차단. env 지정 관리자는 UI에서 강등·비활성 불가.

## 도메인 핵심
- **템플릿 2종**: `project_tracker`(event 트리거, "메일 분석·요약 관리" — **한 에이전트에 이슈 보드(kanban)+타임라인 2개 뷰 탭**), `mail_scheduler`(schedule).
- 새 템플릿 = `app/templates/<key>/` 모듈 + `framework/registry.load_builtin_templates`에 등록. `ViewSpec.views`로 다중 뷰 탭 선언.
- **공유 메일 분석**: `mail_records`(메일함 단위, unique `(mailbox,message_id)`)에 원문+분석 캐시. 분석은 **인용 thread 제거 후 현재 메일만**(`services/mailtext.strip_quoted`). 카테고리는 메일함 단위 공유(에이전트 categories 합집합). `services/mail_analysis.get_or_analyze`가 캐시 진입점. kanban은 `projects.source_message_id`로 원문 링크, 타임라인은 `mail_records` 직접 조회.

## 이번 세션 반영 (현재 상태 요약)
운영 중(실서비스 시작). 큰 변경들:

- **분석 에이전트(project_tracker)**
  - 대상 메일함은 **항상 소유자 본인 메일**로 고정(agents 라우트에서 주입). **계정당 1개만** 생성 가능(중복 시 400, 추가 화면 카드 비활성).
  - **메일 1건 = 카드 1개**(`source_message_id` 멱등 업서트). 신규 카드 기본 상태 **storyboard**. 고객사만 식별돼도 카드 생성(프로젝트 미상="(미지정)"). 칸반 컬럼 4단(storyboard/active/on_hold/completed; **cancelled 컬럼 제거**).
  - 분석에 **키워드+유사어**(검색 누락 방지, 예 음성인식↔STT), **수신 역할**(to=직접수신/cc=참조), 수신/참조 전체 저장. 회사(llsollu) 컨텍스트·수신/참조자 반영.
  - **카테고리** = 사용자 지정 자동 태그(선택) + 항상 "미지정". **이슈 분류(필수)** = 분야별 추천(개발/영업/PM/기획/경영진/인사/재무/행정) 커스터마이즈(`resolve_issue_types`).
  - 원문 모달: HTML 정리·수신/참조 전체 표시. "최신 메일 분석" 버튼 = 최근 N건 중 미분석분 일괄 처리.
- **스케줄러(mail_scheduler)**: 참조 파일 URL **선택**. **오류 알림 메일**(`alert_email` 기본 발신자 본인) — 개별 발송 실패 + **run-level(파일 소실·필요 데이터 필드 소실)**, 원문 첨부·미수집은 `<데이터 미수집>` 표시. 뷰 트리거/규칙에 파일 제목 링크·발송기준일·오류 알림 표시.
- **홈 대시보드**(`GET /dashboard`): 에이전트 구성별 섹션 조립, 서버 집계+시간창(7/30/90일), 인라인 SVG, 60초 폴링. "미해결 이슈"=스토리보드+진행 중+보류 카드 합(칸반과 동일).
- **관리자 페이지**(`/admin`, `routes/admin.py`): 사용자·에이전트 현황·LLM 사용량·운영 상태·데이터 용량 + 수동 prune/archive.
- **장기 운용**: projects API N+1 제거·`archived_at` 제외·반환 상한·복합 인덱스, 칸반 증분 렌더+60초 폴링, 타임라인 `useInfiniteQuery` 커서 페이지네이션, cron `prune_agent_runs`(90일)·`archive_projects`(완료 30일), 폴링 overlap+`top=50`+엄격 최신만(경계 재큐 버그 수정), `llm_jobs` 토큰 적재.
- **DB 수동 마이그레이션 이력(psql ALTER)**: `mail_records`·`projects`.keywords, `mail_records`.{to_recipients,cc_recipients,recipient_role}, `projects`.{from_name,from_address,recipient_role,archived_at}, `users`.{is_admin,is_active}. `llm_jobs` 테이블은 `init_db`로 생성. 인덱스 여러 개 수동 생성.
- 파비콘 = `frontend-react/public/logo.png`.

## Git
- 원격 SSH: `github.com:llsollu/llsollu-email-agent`, 브랜치 `main`. 커밋 메시지는 gitmoji 코드(`:sparkles:` 등) + Co-Authored-By 트레일러 관례.
