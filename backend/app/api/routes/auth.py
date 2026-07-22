"""인증 라우트. 사내 이메일 로그인 + JWT 세션 쿠키.

'회사 이메일 입력 → 이후 자동 로그인'을 만족: 최초 로그인 시 사용자 생성/조회 후
장기 세션 쿠키를 발급하여 재방문 시 자동 로그인된다.
(Entra OIDC 로 교체할 경우 이 라우트만 OIDC 콜백으로 바꾸면 됨.)
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import SESSION_COOKIE, get_current_user
from app.config import settings
from app.db import get_db
from app.models import User
from app.schemas.models import LoginRequest, UserOut
from app.security import create_session_token

router = APIRouter()


@router.post("/auth/login", response_model=UserOut)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> User:
    email = body.email.lower()
    domain = email.split("@")[-1]
    if domain != settings.allowed_email_domain:
        raise HTTPException(status_code=403, detail=f"@{settings.allowed_email_domain} 계정만 허용됩니다")

    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if user is None:
        user = User(email=email, display_name=email.split("@")[0])
        db.add(user)
        await db.flush()
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    token = create_session_token(email=user.email, sub=str(user.id))
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="lax",
        max_age=settings.jwt_expire_hours * 3600,
    )
    return user


@router.post("/auth/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
