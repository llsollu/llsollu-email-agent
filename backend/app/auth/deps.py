"""인증 의존성. 세션 쿠키(JWT)에서 현재 사용자 해석."""

from __future__ import annotations

import uuid

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.security import decode_session_token

SESSION_COOKIE = "session"


async def get_current_user(
    session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not session:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    payload = decode_session_token(session)
    if not payload:
        raise HTTPException(status_code=401, detail="세션이 유효하지 않습니다")
    res = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")
    return user
