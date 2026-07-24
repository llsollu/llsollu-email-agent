# 07. 프론트엔드 마이그레이션: Flutter(Dart) → React + Tauri

현재 Flutter Web 기반 프론트엔드를 **React(Vite + TypeScript) + Tauri** 기반으로 전환하기 위한 계획서다.
백엔드(FastAPI)·데이터 모델·에이전트 프레임워크는 그대로 두고 **프론트엔드만 교체**한다.

---

## 1. 배경과 목표

### 왜 바꾸나
- **텍스트 렌더링 선명도**: Flutter Web(CanvasKit)은 Skia로 글자를 직접 래스터화해 네이티브 HTML보다 흐릿하다. React(DOM) 는 브라우저/웹뷰 네이티브 렌더링이라 또렷하다. (기존에 지적된 문제의 근본 해결)
- **웹 개발 생산성·인력 풀**: HTML/CSS/JS 생태계, 컴포넌트 라이브러리, 드래그앤드롭·차트 등 성숙한 도구 활용.
- **참조 자산 재사용**: `email-agent-master`의 순수 HTML 대시보드를 React로 그대로 이식 가능.
- **네이티브 데스크톱 배포**: Tauri 로 경량(수 MB) 데스크톱 앱(.msi/.dmg/.deb) 배포. Electron 대비 가볍다.

### 목표
1. 현재 화면·기능을 **기능 동등(feature parity)** 으로 재구현.
2. **웹(사내망 서빙)과 데스크톱(Tauri)** 를 하나의 React 코드베이스로 지원.
3. 마이그레이션 각 단계가 **독립적으로 데모 가능**하고, 전환 중에도 기존 Flutter 앱과 병행 가능.

### 비목표
- 백엔드 API 스펙 변경 최소화(인증 방식만 데스크톱 대응으로 확장).
- 신규 기능 추가 금지(이관 완료 후 별도 진행).

---

## 2. 현행 프론트엔드 요약 (이관 대상)

- **스택**: Flutter Web, Riverpod(상태), Dio(HTTP). `frontend/build/web` 를 FastAPI 컨테이너 `/app/web` 에 바인드 마운트하여 **동일 오리진**으로 서빙.
- **인증**: 로그인 시 서버가 JWT를 **httpOnly 세션 쿠키**(`session`, SameSite=Lax)로 발급 → 이후 `/me` 로 자동 로그인. IP 화이트리스트 미들웨어로 사내망 제한.
- **폰트**: Pretendard(CDN)를 런타임 로드.

### 화면·위젯 인벤토리 (`frontend/lib`)

| Flutter 파일 | 역할 |
|---|---|
| `main.dart` | 앱 진입, 테마, ScrollBehavior, `_AuthGate`(/me), Pretendard 로드 |
| `theme.dart` | 색/타이포/컴포넌트 테마(Office 블루, 8px 라운드) |
| `screens/login_screen.dart` | 로그인(이메일/비번, 이메일 저장, 자동 로그인, 애니메이션 배경, 비번 설정 다이얼로그) |
| `screens/home_screen.dart` | 사이드바 + 우측 뷰 라우팅 |
| `screens/add_agent_screen.dart` | 템플릿 카드 그리드 → 설정 |
| `screens/kanban_screen.dart` | 분류·요약 대시보드(칸반, 드래그 상태변경, 검색/분류필터/정렬, 통계, 상세 모달, 드라이런) |
| `screens/scheduler_screen.dart` | 메일 스케줄러 대시보드(규칙, 스케줄 on/off, 실행 로그(한글), 드라이런) |
| `widgets/mail_scheduler_form.dart` | 메일 스케줄러 2단계 마법사(컬럼 드래그, {{토큰}}, 친화적 주기, 검증) |
| `widgets/classifier_form.dart` | 분류·요약 설정(카테고리, 카드 타이틀 선택) |
| `widgets/config_form.dart` | config_schema 기반 범용 폼 |
| `widgets/settings_dialog.dart` | 설정 열람/수정 다이얼로그 |
| `widgets/view_header.dart` | 공통 헤더(제목 + 설정 버튼 + 액션) |
| `widgets/animated_background.dart` | 로그인 배경 블롭 애니메이션 |
| `widgets/schedule_util.dart` | 친화적 주기 ↔ cron 변환/표시 |
| `models/models.dart` | DTO(User/Template/ConfigField/Agent/Project/Issue/Run) |
| `api/api_client.dart` | REST 클라이언트 |
| `state/providers.dart` | Riverpod providers |
| `util/local_store*.dart` | 이메일 저장(localStorage) |

### API 계약 (모두 `/api` 하위)

| 메서드 · 경로 | 용도 |
|---|---|
| `POST /auth/check-email` | 이메일 상태(existing/needs_setup/not_company) |
| `POST /auth/login` | 이메일+비번 로그인(쿠키 발급) |
| `POST /auth/register` | 사내 계정 최초 비번 설정 |
| `POST /auth/logout` / `GET /me` | 로그아웃 / 현재 사용자 |
| `GET /templates` · `GET /templates/{key}/config-schema` | 템플릿 목록·스키마 |
| `POST /templates/mail_scheduler/columns` | 참조 파일 컬럼 미리보기 |
| `GET/POST /agents` · `GET/PATCH/DELETE /agents/{id}` | 에이전트 CRUD |
| `POST /agents/{id}/run` | 수동 실행/드라이런 |
| `GET /agents/{id}/projects` · `PATCH /agents/{id}/projects/{pid}/status` | 칸반 |
| `GET /agents/{id}/runs` · `GET/PATCH /agents/{id}/schedule` | 스케줄러 |

---

## 3. 대상 스택 결정

| 영역 | 선택 | 비고 |
|---|---|---|
| 번들러/언어 | **Vite + React 18 + TypeScript** | 빠른 HMR, 표준 |
| 데스크톱 | **Tauri 2.x** (Rust) | 경량 네이티브, 시스템 웹뷰 |
| 서버 상태 | **TanStack Query** | 캐싱/로딩/무효화 |
| 클라이언트 상태 | **Zustand** (경량) | 인증 사용자/전역 UI |
| 라우팅 | **React Router** | 로그인/홈/뷰 |
| 스타일 | **Tailwind CSS + shadcn/ui**(Radix 기반, 코드 소유) | 새 테마 토큰(§3.1)을 CSS 변수로 |
| 드래그앤드롭 | **@dnd-kit/core** | 칸반 상태 변경, 스케줄러 토큰 삽입 |
| HTTP | **fetch 래퍼**(웹) / **@tauri-apps/plugin-http**(데스크톱) | 아래 인증 절 참고 |
| 폼 | 경량 자체 구현 or react-hook-form | 검증 포함 |
| 폰트 | Pretendard (CDN `@font-face`) | DOM 렌더 → 선명 |

### 3.1 새 테마 방향 (Office 블루 폐기)

기존 Office 블루를 버리고 **산뜻하고 발랄한 스타트업 무드**로 새로 잡는다. 방향:
- **비비드하지만 친근한 프라이머리 + 따뜻한 악센트**, 밝은 오프화이트 배경, 큼직한 라운드(12~16px), 부드러운 그림자, 포인트에만 가벼운 그라데이션.
- 네이티브 DOM 렌더라 폰트가 또렷 → 굵기·자간을 경쾌하게.

**제안 팔레트(기본값, Phase 0에서 1~2안 시안 후 확정)** — CSS 변수로 정의:

| 토큰 | 값 | 용도 |
|---|---|---|
| `--primary` / hover | `#6D5EF6` / `#5B4BE0` | 바이올렛 포인트 |
| `--accent` | `#FF7A59` | 코랄(발랄한 강조) |
| `--mint` | `#2DD4BF` | 보조 포인트 |
| `--bg` / `--surface` | `#FBFAFF` / `#FFFFFF` | 배경/카드 |
| `--ink` / `--muted` / `--line` | `#1A1A2E` / `#6B7280` / `#ECECF5` | 글자/보조/보더 |
| 상태색 | storyboard=바이올렛, active=`#22C55E`, on_hold=`#F59E0B`, completed=슬레이트, cancelled=`#F43F5E` | 칸반 |

로그인 배경 애니메이션은 새 팔레트(바이올렛/민트/코랄 블롭)로 재구성.

---

## 4. 웹 · 데스크톱 동시 지원 전략

하나의 React 코드베이스를 두 타깃으로 빌드한다.

- **웹 빌드** (`vite build`): 정적 산출물(`dist/`)을 FastAPI `/app/web` 에 바인드 마운트 → **동일 오리진**, 기존 배포 방식 유지(사내망 IP 화이트리스트 그대로 동작).
- **데스크톱 빌드** (`tauri build`): 시스템 웹뷰로 `dist/` 를 로드하고, **API 베이스 URL을 사내 서버로 설정**해 원격 호출. 설치형 바이너리 배포.

API 베이스는 환경으로 분기:
```ts
// 웹(동일 오리진) → '', 데스크톱 → 사내 서버 절대 URL
export const API_BASE = import.meta.env.VITE_API_BASE ?? '';
export const apiRoot = `${API_BASE}/api`;
```

---

## 5. 인증 · 네트워크 (가장 중요한 변경점)

현재는 **동일 오리진 httpOnly 쿠키** 라 브라우저에서 자연스럽게 동작한다. React 전환 시:

- **웹 빌드**: 동일 오리진 유지 → **쿠키 방식 그대로**. `fetch(..., { credentials: 'include' })`.
- **데스크톱(Tauri)**: 웹뷰 오리진(`tauri://localhost` 등)과 API 서버 오리진이 달라 **httpOnly 쿠키가 교차 오리진에서 신뢰되기 어렵다.** 두 가지 방안:
  1. **(권장) 토큰 방식 병행** — 로그인/가입 응답 본문에 JWT를 함께 반환하고, 데스크톱은 이를 저장(Tauri Store/OS 키체인) 후 `Authorization: Bearer <jwt>` 헤더로 호출. 백엔드 `get_current_user` 가 **쿠키 또는 Bearer 둘 다** 허용하도록 확장.
  2. Tauri HTTP 플러그인의 쿠키 저장소 사용(구성 복잡) — 비권장.

### 필요한 백엔드 최소 변경(별도 승인 후)
- `app/auth/deps.py`: `Authorization: Bearer` 토큰도 세션으로 해석(쿠키와 동일 JWT 검증).
- `auth.py`: `login`/`register` 응답에 `access_token` 필드 추가(웹은 무시, 데스크톱만 사용).
- CORS: 데스크톱 오리진 허용(토큰 방식이면 `credentials` 불필요 → 단순).
- IP 화이트리스트: 사내 PC의 Tauri 앱은 사내 IP라 통과. 원격 사용 시 정책 재검토.

> 이 변경들은 **문서 승인 후 별도 커밋**으로 진행한다. 웹 전환만 먼저 하면 백엔드 무변경으로 가능.

---

## 6. 컴포넌트 매핑 (Flutter → React)

| Flutter | React (제안 경로) |
|---|---|
| `main.dart` + `_AuthGate` | `src/App.tsx`, `src/auth/AuthGate.tsx` |
| `theme.dart` | `src/theme.css`(CSS 변수) + `tailwind.config.js` |
| `login_screen` + `animated_background` | `src/pages/Login.tsx` + `AnimatedBackground.tsx`(CSS/canvas) |
| `home_screen` | `src/layout/AppShell.tsx`(Sidebar + Outlet) |
| `add_agent_screen` | `src/pages/AddAgent.tsx`(TemplateGrid + 폼 분기) |
| `kanban_screen` | `src/pages/Kanban.tsx` + `KanbanColumn/Card/DetailModal` (@dnd-kit) |
| `scheduler_screen` | `src/pages/Scheduler.tsx` |
| `mail_scheduler_form` | `src/forms/MailSchedulerForm.tsx`(2단계, dnd 토큰) |
| `classifier_form` | `src/forms/ClassifierForm.tsx` |
| `config_form` | `src/forms/ConfigForm.tsx` |
| `settings_dialog` | `src/components/SettingsDialog.tsx` |
| `view_header` | `src/components/ViewHeader.tsx` |
| `schedule_util` | `src/lib/schedule.ts` |
| `models.dart` | `src/lib/types.ts` |
| `api_client` | `src/lib/api.ts` (+ TanStack Query 훅 `src/hooks/`) |
| `providers` | `src/store/auth.ts`(Zustand) + Query 캐시 |
| `util/local_store` | `localStorage` 직접(웹) / Tauri Store(데스크톱) |

---

## 7. 디렉터리 구조 제안

```
frontend-react/                # 기존 frontend/(Flutter)와 병행, 완료 후 교체
  src-tauri/                   # Tauri(Rust) — tauri.conf.json, main.rs
  src/
    main.tsx  App.tsx
    theme.css  index.css
    lib/       api.ts  types.ts  schedule.ts
    store/     auth.ts
    hooks/     useAgents.ts  useProjects.ts  ...
    auth/      AuthGate.tsx
    layout/    AppShell.tsx  Sidebar.tsx
    components/ ViewHeader.tsx  SettingsDialog.tsx  Badge.tsx  ...
    forms/     ConfigForm.tsx  MailSchedulerForm.tsx  ClassifierForm.tsx
    pages/     Login.tsx  AddAgent.tsx  Kanban.tsx  Scheduler.tsx
  index.html   vite.config.ts  tailwind.config.js  package.json
```

---

## 8. 단계별 로드맵 (각 단계 데모 가능)

> 노출 정책: **개발 내내 로컬(`npm run dev` / `tauri dev`)에서만 검증**하고, 완성 후 서버 `/`를 **한 번에 교체(단일 컷오버)**. 전환 중 별도 서버 경로 병행 노출은 하지 않는다.

### Phase 0 — 스캐폴딩 + 테마 시안 (1일)
- `frontend-react` 에 Vite+React+TS, Tailwind, **shadcn/ui**, Router, TanStack Query, Zustand, dnd-kit 설치.
- Tauri 2.x 초기화(`src-tauri`), 개발 실행 확인.
- API 베이스/`fetch` 래퍼, Pretendard `@font-face`.
- **새 테마 시안 1~2안**(§3.1 팔레트 기반)을 버튼/카드/입력 샘플로 만들어 확정.
- **데모**: 빈 앱이 웹·데스크톱에서 뜨고 `/api/health` 성공 + 테마 시안 확인.

### Phase 1 — 인증·셸 (1일)
- `api.ts`, `types.ts`, Zustand 인증 스토어, `AuthGate`(/me), `Login`(check-email→login/register 분기, 이메일 저장, 자동 로그인, 애니메이션 배경).
- `AppShell`(사이드바 + 라우팅), `ViewHeader`.
- **데모**: 로그인→홈, 에이전트 목록 표시, 로그아웃.

### Phase 2 — 분류·요약 칸반 (1.5일)
- `Kanban`: 검색/분류필터/분류·업데이트·고객사 정렬, 통계, 상태 컬럼(스토리보드~취소), 카드(배지/우선순위/이슈칩/타이틀 선택), **@dnd-kit 드래그로 상태 변경**(낙관적 업데이트+롤백), 상세 모달, 드라이런(폴링 결과 모달).
- **데모**: 실제 데이터로 칸반 조작.

### Phase 3 — 스케줄러 + 생성/설정 폼 (2일)
- `Scheduler`(규칙 표시, 스케줄 토글, 실행 로그 한글화, 드라이런).
- `AddAgent`(템플릿 카드 그리드), `MailSchedulerForm`(2단계, 컬럼/특수(`{{이번달}}` 등) 드래그, 친화적 주기, {{ }} 검증), `ClassifierForm`, `ConfigForm`, `SettingsDialog`.
- `schedule.ts`(cron 변환) 이식.
- **데모**: 두 종류 에이전트 생성·수정·삭제.

### Phase 4 — 마감·병행 검증 (1일)
- 반응형, 마우스 스크롤, 빈/로딩/에러 상태, 접근성, 폰트/여백 미세 조정.
- 기존 Flutter 앱과 화면·동작 대조(parity 체크리스트).
- **데모**: 전체 시나리오 완주.

### Phase 5 — 데스크톱 인증 + 패키징 + 컷오버 (1일, 백엔드 변경 포함)
- 백엔드: Bearer 토큰 허용 + 로그인/가입 응답에 토큰(§5).
- Tauri 빌드/서명/설치본, 자동 업데이트(선택).
- docker-compose 볼륨을 `frontend-react/dist` 로 교체, 웹 서빙 전환.
- 안정화 후 `frontend/`(Flutter) 제거.

**예상 총 소요: 약 7~8 인·일**(폼/검증/드래그 세부에 따라 변동).

---

## 9. 배포 변경

- **웹**: `deploy/docker-compose.yml` 의
  `../frontend/build/web:/app/web:ro` → `../frontend-react/dist:/app/web:ro`.
  빌드: `npm ci && npm run build`.
- **데스크톱**: CI 또는 로컬에서 `tauri build` → 플랫폼별 설치본 배포. `VITE_API_BASE=http://<사내서버>:8000` 주입.
- FastAPI 정적 서빙/`index.html` 폴백은 그대로 사용(SPA 라우팅은 base href + 서버 폴백 확인).

---

## 10. 리스크 · 트레이드오프

| 항목 | 내용 | 완화 |
|---|---|---|
| 툴체인 증가 | Node + Rust(Tauri) 2개 | 웹 전환 먼저, 데스크톱은 Phase 5로 분리 |
| 인증 모델 | 데스크톱 교차 오리진 쿠키 문제 | Bearer 토큰 병행(§5) |
| 재구현 범위 | 드래그·폼·검증·주기변환·테마 재작성 | 참조 HTML 대시보드 재사용, 단계별 이식 |
| 단일 코드베이스 상실 | Flutter의 멀티플랫폼 포기 | 웹+Tauri로 실사용 타깃 커버 |
| 병행 기간 유지비 | 두 프론트 공존 | 짧게(Phase 2~4) 유지 후 즉시 컷오버 |
| 기능 회귀 | parity 누락 | §8 Phase 4 대조 체크리스트 |

### 이점
- 네이티브 DOM 렌더 → **텍스트 선명도 문제 해소**.
- 웹 생태계/인력, 참조 자산 재사용, 경량 데스크톱 배포.

---

## 11. 파리티 체크리스트 (Phase 4)

- [ ] 로그인 3분기(existing/needs_setup/not_company) + 이메일 저장 + 자동 로그인 + 배경 애니메이션
- [ ] 사이드바/뷰 라우팅/로그아웃, "추후 변경 가능" 안내
- [ ] 칸반: 드래그 상태변경, 검색, 분류 필터, 정렬(업데이트/분류/고객사), 통계, 카드 타이틀 선택, 상세 모달, 드라이런
- [ ] 스케줄러: 규칙 표시(확인 주기 한글), 스케줄 토글, 실행 로그 한글, 드라이런, CC 표시
- [ ] 메일 스케줄러 생성 2단계: 컬럼/특수 토큰 드래그, `{{ }}` 검증, 친화적 주기, 다중 수신자/참조, 발신=본인
- [ ] 분류기 생성: 카테고리, 카드 타이틀 선택
- [ ] 설정 다이얼로그(수정/삭제), 마우스 스크롤, KST 시간 표시
- [ ] 웹(동일 오리진 쿠키) + 데스크톱(Bearer) 인증 동작

---

## 12. 결정 사항 (확정, 2026-07-24)

| # | 항목 | 결정 |
|---|---|---|
| 1 | 데스크톱 지원 | **포함** — Tauri 데스크톱 앱까지 배포. §5 백엔드 Bearer 토큰 인증 변경 범위에 포함. |
| 2 | UI 라이브러리 | **Tailwind CSS + shadcn/ui**(Radix 기반, 코드 소유·자유 테마). |
| 3 | 전환 중 노출 | **로컬에서만 검증 → 완성 후 단일 컷오버.** 서버 `/next` 병행 노출 없음. |
| 4 | 디자인 테마 | **Office 블루 폐기 → 산뜻·발랄한 스타트업 신규 테마**(§3.1). |
