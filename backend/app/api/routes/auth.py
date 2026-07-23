"""인증 라우트. 사내 이메일 + 비밀번호 로그인 + JWT 세션 쿠키.

로그인 흐름(프론트가 /auth/check-email 로 분기 판단):
  1) 입력 이메일이 DB에 없고 Graph(사내 디렉터리)에도 없음 → not_company (경고)
  2) DB에 없고 Graph에는 있음 → needs_setup → /auth/register 로 비밀번호 설정 후 로그인
  3) DB에 있음 → /auth/login 으로 이메일+비밀번호 검증 후 로그인
'자동 로그인(remember)'이면 장기 쿠키, 아니면 세션 쿠키(브라우저 종료 시 만료).
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
from app.schemas.models import (
    CheckEmailRequest,
    CheckEmailResponse,
    LoginRequest,
    RegisterRequest,
    UserOut,
)
from app.security import create_session_token, hash_password, verify_password
from app.services.graph import graph_client

router = APIRouter()


def _domain_ok(email: str) -> bool:
    return email.split("@")[-1] == settings.allowed_email_domain


async def _is_company_user(email: str) -> bool:
    """Graph 디렉터리에 존재하는 사내 계정인지. Graph 미설정 시 도메인만으로 판단."""
    if not settings.graph_configured:
        return _domain_ok(email)
    try:
        return await graph_client.find_user(email) is not None
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"사내 계정 확인 중 오류: {e}") from e


def _issue_session(response: Response, user: User, remember: bool) -> None:
    token = create_session_token(email=user.email, sub=str(user.id))
    # remember=True 면 장기 쿠키(max_age), 아니면 세션 쿠키(브라우저 종료 시 삭제).
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="lax",
        max_age=(settings.jwt_expire_hours * 3600 if remember else None),
    )


@router.post("/auth/check-email", response_model=CheckEmailResponse)
async def check_email(body: CheckEmailRequest, db: AsyncSession = Depends(get_db)) -> CheckEmailResponse:
    email = body.email.lower()
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    # DB에 계정이 있으면(비밀번호 유무와 무관) 항상 비밀번호 검증 경로로 → 로그인/실패만.
    # 비밀번호 설정창(needs_setup)은 DB에 아예 없는 신규 회사 계정에만 나온다.
    if user is not None:
        return CheckEmailResponse(status="existing", display_name=user.display_name)
    if not _domain_ok(email):
        return CheckEmailResponse(status="not_company")
    if await _is_company_user(email):
        return CheckEmailResponse(status="needs_setup")
    return CheckEmailResponse(status="not_company")


@router.post("/auth/login", response_model=UserOut)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> User:
    email = body.email.lower()
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="가입되지 않은 계정입니다")
    if not user.password_hash:
        raise HTTPException(status_code=401, detail="비밀번호가 설정되지 않은 계정입니다. 관리자에게 문의하세요")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    _issue_session(response, user, body.remember)
    return user


@router.post("/auth/register", response_model=UserOut)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)) -> User:
    email = body.email.lower()
    if not body.password or len(body.password) < 4:
        raise HTTPException(status_code=400, detail="비밀번호는 4자 이상이어야 합니다")
    if not _domain_ok(email):
        raise HTTPException(status_code=403, detail="정확한 회사 메일주소를 입력하세요")

    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if user is not None and user.password_hash:
        raise HTTPException(status_code=409, detail="이미 가입된 계정입니다. 로그인해 주세요")

    # 서버측 재검증: 클라이언트 상태를 신뢰하지 않고 Graph 로 사내 계정 여부 확인.
    if not await _is_company_user(email):
        raise HTTPException(status_code=403, detail="정확한 회사 메일주소를 입력하세요")

    if user is None:
        user = User(email=email, display_name=email.split("@")[0])
        db.add(user)
    user.password_hash = hash_password(body.password)
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()
    await db.refresh(user)
    _issue_session(response, user, body.remember)
    return user


@router.post("/auth/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
