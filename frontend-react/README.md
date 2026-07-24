# frontend-react (React + Tauri)

Flutter 프론트엔드를 대체하기 위한 신규 프론트엔드. 마이그레이션 완료 전까지 기존 `frontend/`(Flutter)와 병행한다.
계획: [`docs/07-react-tauri-migration.md`](../docs/07-react-tauri-migration.md)

## 스택
Vite + React 18 + TypeScript · Tailwind CSS v4 · TanStack Query · Zustand · React Router · @dnd-kit · Tauri 2.

## 사전 준비 (Node)
Node는 nvm 사용을 권장:
```bash
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"   # nvm 로드
npm install
```

## 웹 개발 / 빌드
```bash
npm run dev      # http://localhost:5173, /api → http://localhost:8000 프록시
npm run build    # dist/ 생성 (배포 시 FastAPI /app/web 로 마운트)
```
- 백엔드(FastAPI)가 `:8000`에 떠 있어야 `/api` 호출이 동작한다.

## 데스크톱 (Tauri)
```bash
npm run tauri:dev     # 개발 실행
npm run tauri:build   # 설치본 빌드
```
사전요건:
- **Rust 툴체인**(rustup) — 사용자 공간 설치, sudo 불필요.
- 플랫폼 웹뷰/빌드 도구:
  - **Windows**: Microsoft Edge WebView2 Runtime + MSVC 빌드 도구.
  - **macOS**: Xcode Command Line Tools.
  - **Linux**: `webkit2gtk-4.1`, `libgtk-3-dev`, `build-essential`, `libssl-dev` 등 (설치에 관리자 권한 필요).
- 데스크톱 배포는 사내 PC(대개 Windows)나 CI에서 빌드한다. 원격 API 주소는 `VITE_API_BASE` 로 주입:
  ```bash
  VITE_API_BASE=http://<사내서버>:8000 npm run tauri:build
  ```

## 현재 상태
Phase 0 — 스캐폴딩 + 새 테마 시안 + 백엔드 헬스 연동 확인 완료.
