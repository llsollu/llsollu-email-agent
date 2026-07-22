# LLSOLLU Email Agent Platform

사내 여러 부서의 사용자가 **이메일 기반 에이전트**를 템플릿으로 손쉽게 만들어 쓰는 멀티테넌트 플랫폼.

사용자는 웹에서 클릭 몇 번으로 템플릿을 골라 자기만의 에이전트를 구성·운영한다. 각 에이전트는 정해진 트리거(새 메일 수신 또는 지정 시각)에 따라 자동으로 동작하고, 전용 대시보드에서 결과를 확인·관리한다.

> 이 저장소는 **설계 문서(docs/) + 구현 코드(backend/, frontend/, deploy/)**를 담는다.
> 실행 방법은 [backend/README.md](backend/README.md), 배포는 [deploy/docker-compose.yml](deploy/docker-compose.yml) 참고.

---

## 템플릿 기반 Agent 추가

플랫폼은 **템플릿**을 제공하고, 사용자는 템플릿을 인스턴스화해 **에이전트**를 만든다. 기본 제공 템플릿은 다음 2종이며, 향후 계속 추가된다.

| 템플릿 | 설명 | 뷰 |
|---|---|---|
| **project_tracker** — 메일 분류·요약 → 고객사 프로젝트 관리 | 지정한 메일함의 수신 메일을 LLM으로 분류·요약해 고객사/프로젝트/이슈를 자동 갱신 | **칸반 보드** |
| **mail_scheduler** — 메일 자동 발송 스케줄링 | 참조 스프레드시트(공유 파일)와 발행일 규칙을 바탕으로 정해진 시각에 지정 양식의 메일을 자동 발송하고, 필수 데이터 누락 시 담당자에게 알림 | **스케줄러 패널**(트리거·규칙·참조파일·실행 로그·on/off) |

**핵심 설계 목표**는 "새 템플릿을 백엔드 모듈 한 개(+ 필요 시 프론트 뷰 하나)로 추가할 수 있는 프레임워크"를 만드는 것이다. 두 기본 템플릿도 이 프레임워크 위의 플러그인이다.

---

## 문서 색인

| 문서 | 내용 |
|---|---|
| [docs/01-architecture.md](docs/01-architecture.md) | 시스템 구성요소, 트리거→실행 파이프라인, 기술 스택, 배포 토폴로지 |
| [docs/02-agent-framework.md](docs/02-agent-framework.md) | **에이전트 템플릿 프레임워크** — 5요소 추상화와 확장 방법 (핵심) |
| [docs/03-data-model.md](docs/03-data-model.md) | DB 엔티티/스키마, 멀티테넌트 격리 |
| [docs/04-user-flow.md](docs/04-user-flow.md) | 화면 흐름 + 각 단계의 API 호출 |
| [docs/05-roadmap.md](docs/05-roadmap.md) | 구현 단계와 현재 상태 |
| [docs/06-constraints-and-risks.md](docs/06-constraints-and-risks.md) | 확정 결정·제약·리스크 |

## 한눈에 보는 스택

- **백엔드**: FastAPI (uv, Python 3.12) · SQLAlchemy 2.0(async) + Alembic · Pydantic v2
- **데이터**: PostgreSQL 16 · Redis 7
- **비동기 처리**: Redis 큐(arq) + 워커 · LLM 호출은 Redis 동시성 게이트 경유
- **스케줄러/수신**: 워커의 매분 cron이 도래한 스케줄을 큐에 투입하고, 메일함을 폴링해 수신 메일을 처리
- **메일 I/O**: Microsoft Graph (앱 전용 client credentials) — 수신(폴링, webhook 지원)·발송
- **LLM**: 사내SLM (OpenAI 호환 `http://<사내-LLM-호스트-endpoint>`)
- **인증**: 회사 이메일 로그인 + JWT 세션 쿠키 · **백엔드 IP 화이트리스트**(사내망 전용)
- **프론트엔드**: Flutter — Web(+ 향후 Desktop/macOS)
- **배포**: Docker Compose (리버스 프록시 없음 — 서버 IP:포트 직접 접속)

### 접속
사내망에서 브라우저로 `http://<서버IP>:8000/` — 회사 이메일로 로그인. Web 산출물은 API가 같은 오리진에서 서빙한다.

### 확정 전제
- 사용자 약 10명 규모 (리소스 병목 없음)
- 인증은 회사 이메일(`@llsollu.com`) 로그인 + 장기 세션 쿠키로 재방문 시 자동 로그인
- LLM은 **사내** 추론 서버 → 메일 데이터가 외부로 나가지 않음
- 도메인/리버스 프록시 없이 서버 IP:포트 직접 접속, 접근 제어는 백엔드 IP 화이트리스트
- 모든 뷰 화면에 **⚙️ 설정 버튼** → 생성 시 설정을 열람·수정·업데이트
