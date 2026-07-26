"""인증 의존성. 세션 쿠키(JWT)에서 현재 사용자 해석."""

from __future__ import annotations

import uuid

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models import User
from app.security import decode_session_token

SESSION_COOKIE = "session"


def is_effective_admin(user: User) -> bool:
    """DB 플래그 또는 ADMIN_EMAILS 부트스트랩 → 관리자."""
    return bool(user.is_admin) or settings.is_bootstrap_admin(user.email)


async def get_current_user(
    session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    # 웹은 httpOnly 세션 쿠키, 데스크톱(Tauri)은 Authorization: Bearer <jwt>.
    token = session
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    payload = decode_session_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="세션이 유효하지 않습니다")
    res = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다. 관리자에게 문의하세요")
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not is_effective_admin(user):
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    return user
