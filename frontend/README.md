# Frontend — LLSOLLU Email Agent (Flutter)

Web + Desktop(Windows/Linux) + macOS 단일 코드베이스. 상태관리 Riverpod, HTTP Dio.

## 구조

```
lib/
  config.dart              API 베이스 URL (--dart-define=API_BASE=...)
  main.dart                앱 + AuthGate(세션 확인 → 자동 로그인)
  api/api_client.dart      백엔드 REST 클라이언트
  models/models.dart       DTO
  state/providers.dart     Riverpod providers
  screens/
    login_screen.dart      회사 이메일 로그인
    home_screen.dart       좌측 에이전트 목록 + [+ 추가], 우측 뷰
    add_agent_screen.dart  템플릿 선택 → 설정 입력 → 생성
    kanban_screen.dart     T1 뷰 (view_type=kanban)
    scheduler_screen.dart  T2 뷰 (view_type=scheduler_panel)
  widgets/
    config_form.dart       config_schema 기반 동적 폼 (생성/설정 공용)
    settings_dialog.dart   ⚙️ 설정 다이얼로그 (열람·수정·삭제)
    view_header.dart       모든 뷰 상단 공통 헤더 + ⚙️ 버튼
```

## 프로젝트 초기화 (플랫폼 러너 생성)

이 폴더에는 `lib/`, `pubspec.yaml` 만 포함되어 있습니다. 플랫폼별 러너(web/, windows/, linux/, macos/)는
Flutter SDK 설치 후 아래로 생성하세요.

```bash
cd frontend
flutter create . --platforms=web,windows,linux,macos --project-name llsollu_email_agent
flutter pub get
```

## 실행 / 빌드

```bash
# 개발 (웹, 서버 IP 지정)
flutter run -d chrome --dart-define=API_BASE=http://<SERVER_IP>:8000

# 웹 빌드 → 백엔드가 /app/web 에서 서빙 (deploy/docker-compose 볼륨)
flutter build web --dart-define=API_BASE=

# 데스크톱 / macOS
flutter build windows --dart-define=API_BASE=http://<SERVER_IP>:8000
flutter build linux   --dart-define=API_BASE=http://<SERVER_IP>:8000
flutter build macos   --dart-define=API_BASE=http://<SERVER_IP>:8000
```

> Web 을 백엔드가 같은 오리진에서 서빙하면 `API_BASE=` (빈 값) → 상대경로 `/api` 사용, 쿠키 세션이 자연스럽게 동작.
> Desktop/macOS 는 서버 IP 를 API_BASE 로 주입.

## 화면 흐름

로그인 → (좌측)에이전트 목록/추가 → 템플릿 선택 → 설정 → 생성('구성 중…') → 목록에 표시 →
클릭 시 kanban 또는 scheduler_panel → 우상단 ⚙️ 로 설정 열람·수정.

## 새 view_type 추가

`home_screen.dart` 의 `_content()` switch 에 `case '<view_type>'` 추가 후 화면 위젯 작성.
기존 kanban/scheduler_panel 을 재사용하는 템플릿이면 프론트 수정 불필요.
