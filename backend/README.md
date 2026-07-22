# Backend — LLSOLLU Email Agent Platform

FastAPI(uv, Python 3.12) + PostgreSQL + Redis(arq) 기반. 리버스 프록시 없이 `:8000` 직접 노출, IP 화이트리스트는 미들웨어에서 처리.

## 구조

```
app/
  main.py            FastAPI 앱 (미들웨어, /api 라우터, 정적 web 서빙)
  config.py          환경설정 (pydantic-settings)
  db.py              async 엔진/세션
  security.py        IP 화이트리스트 미들웨어 + JWT 세션
  models/            SQLAlchemy 모델 (users, agents, runs, schedules, llm_jobs, T1/T2 도메인)
  schemas/           Pydantic 입출력 스키마
  auth/              세션 인증 의존성
  framework/         에이전트 템플릿 프레임워크 (base/context/registry)  ← 핵심
  templates/
    project_tracker/ T1: 메일 분류·요약 → 칸반
    mail_scheduler/  T2: 발송 스케줄링 (xlsx/matcher/builder)
  services/          llm(Gemma-4), graph(MS Graph), queue(arq), crypto(secret 암호화)
  workers/           arq 워커: run_agent/setup_agent + cron(스케줄 디스패치, 메일 폴링)
  api/routes/        auth, templates, agents, projects(T1), scheduler(T2), webhooks
  tools/             genkey(암호화키), init_db(부트스트랩)
```

## 로컬 실행 (uv)

```bash
cd backend
uv sync                              # 의존성 설치
cp .env.example .env                 # 값 채우기
python -m app.tools.genkey           # SECRET_ENC_KEY 생성 → .env 에 넣기
# postgres/redis 는 별도 기동 (또는 deploy/docker-compose)
python -m app.tools.init_db          # 최초 테이블 생성
uv run uvicorn app.main:app --reload --port 8000
# 워커(별도 터미널)
uv run arq app.workers.worker.WorkerSettings
```

## Docker Compose

```bash
cd deploy
cp ../backend/.env.example ../backend/.env   # 값 채우기 (SECRET_ENC_KEY 필수)
docker compose up -d --build
docker compose exec api python -m app.tools.init_db   # 최초 1회
```

접속: `http://<서버IP>:8000/api/health`

## 주요 환경변수 (.env)

| 키 | 설명 |
|---|---|
| `ALLOWED_NETWORKS`, `ALLOWED_IPS` | 사내망 IP 화이트리스트 |
| `ALLOWED_EMAIL_DOMAIN` | 로그인 허용 도메인 (llsollu.com) |
| `JWT_SECRET`, `SECRET_ENC_KEY` | 세션 서명키 / 비밀 암호화키(Fernet) |
| `DATABASE_URL`, `REDIS_URL` | 데이터 저장소 |
| `LLM_BASE_URL`, `LLM_MODEL` | 사내 Gemma-4 (OpenAI 호환) |
| `GRAPH_TENANT_ID/CLIENT_ID/CLIENT_SECRET` | MS Graph 앱 자격증명 |
| `GRAPH_WEBHOOK_BASE_URL` | 설정 시 webhook 모드, 미설정 시 폴링 모드 |

## API 요약 (모두 `/api` 하위)

- `POST /auth/login {email}` · `POST /auth/logout` · `GET /me`
- `GET /templates` · `GET /templates/{key}/config-schema`
- `GET/POST /agents` · `GET/PATCH/DELETE /agents/{id}` · `POST /agents/{id}/run?dry_run=`
- (T1) `GET /agents/{id}/projects` · `PATCH /agents/{id}/projects/{pid}/status`
- (T2) `GET /agents/{id}/runs` · `GET/PATCH /agents/{id}/schedule`
- `POST /webhooks/graph` (Graph 알림, IP 화이트리스트 예외)

## 새 템플릿 추가

1. `app/templates/<key>/template.py` 에 `AgentTemplate` 구현.
2. `app/templates/<key>/__init__.py` 에서 `register(...)`.
3. `app/framework/registry.load_builtin_templates()` 가 import 하도록 추가.
4. 새 뷰가 필요하면 프론트에 `view_type` 대응 화면 추가(기존 kanban/scheduler_panel 재사용 시 프론트 무변경).
