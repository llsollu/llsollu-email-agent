"""FastAPI 진입점. 리버스 프록시 없이 백엔드가 직접 포트 노출.

- IP 화이트리스트 미들웨어(사내망 제한)
- API 는 /api 하위
- Flutter Web 정적 산출물이 있으면 / 에서 서빙(동일 오리진 → CORS 불필요)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope

from app.api.routes import api_router
from app.framework.registry import all_templates, load_builtin_templates
from app.security import IPWhitelistMiddleware

WEB_DIR = os.getenv("WEB_DIR", "/app/web")


class SPAStaticFiles(StaticFiles):
    """SPA(React Router) 딥링크 대응: 없는 경로는 index.html 로 폴백."""

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # /api 경로는 SPA 폴백에서 제외 → 실제 404(JSON) 유지.
            if exc.status_code == 404 and not path.startswith("api"):
                return await super().get_response("index.html", scope)
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_builtin_templates()
    yield


app = FastAPI(title="LLSOLLU Email Agent Platform", version="0.1.0", lifespan=lifespan)

# CORS: 개발 서버(Vite) 및 Tauri 데스크톱 웹뷰 오리진 허용.
# 웹은 동일 오리진(CORS 불필요), 데스크톱은 Bearer 토큰(쿠키 미사용)으로 호출.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"(http://(localhost|127\.0\.0\.1|192\.168\.[0-9.]+|211\.236\.[0-9.]+|10\.0\.[0-9.]+)(:[0-9]+)?"
        r"|tauri://localhost|https?://tauri\.localhost)"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# IP 화이트리스트는 가장 바깥에서 먼저 검사 (마지막에 추가 = 최외곽)
app.add_middleware(IPWhitelistMiddleware)

app.include_router(api_router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "templates": [t.key for t in all_templates()]}


# React(SPA) 정적 서빙(존재할 때만). /api 는 위 라우터가 먼저 매칭.
if os.path.isdir(WEB_DIR):
    app.mount("/", SPAStaticFiles(directory=WEB_DIR, html=True), name="web")
