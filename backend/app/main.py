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

from app.api.routes import api_router
from app.framework.registry import all_templates, load_builtin_templates
from app.security import IPWhitelistMiddleware

WEB_DIR = os.getenv("WEB_DIR", "/app/web")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_builtin_templates()
    yield


app = FastAPI(title="LLSOLLU Email Agent Platform", version="0.1.0", lifespan=lifespan)

# Flutter Web(별도 오리진에서 개발 서빙 시)용 CORS. 데스크톱/macOS 앱은 브라우저가 아니라 무관.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.[0-9.]+|211\.236\.[0-9.]+)(:[0-9]+)?",
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


# Flutter Web 정적 서빙(존재할 때만)
if os.path.isdir(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
