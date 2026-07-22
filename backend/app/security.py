"""IP 화이트리스트 미들웨어 + JWT 세션 유틸. 리버스 프록시 없이 백엔드에서 접근 제어."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
from datetime import datetime, timedelta, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

ALGO = "HS256"

# 인증/헬스 등 화이트리스트 검사에서 제외할 경로 접두사는 없음 — 전 경로 사내망 제한.
# Graph webhook 검증(validationToken)만 예외 처리한다.


def _client_ip(request: Request) -> str | None:
    # 프록시가 없으므로 request.client.host 가 실제 소스. (있다면 X-Forwarded-For 우선)
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def is_allowed_ip(ip: str | None) -> bool:
    if not ip:
        return False
    if ip in settings.allowed_ips_set:
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for net in settings.allowed_networks_list:
        try:
            if addr in ipaddress.ip_network(net):
                return True
        except ValueError:
            continue
    return False


# Graph webhook 은 외부(Microsoft) IP에서 오므로 IP 화이트리스트를 우회하고
# clientState 로 검증한다. 그 외 전 경로는 사내망으로 제한.
_IP_BYPASS_PREFIXES = ("/api/webhooks/graph",)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith(_IP_BYPASS_PREFIXES):
            if not is_allowed_ip(_client_ip(request)):
                return JSONResponse(status_code=403, content={"detail": "Forbidden (IP not allowed)"})
        return await call_next(request)


def create_session_token(email: str, sub: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_session_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
    except JWTError:
        return None


# ── 비밀번호 해싱(표준 라이브러리 PBKDF2, 외부 의존성 없음) ──
_PBKDF2_ITERS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERS)
    return f"pbkdf2_sha256${_PBKDF2_ITERS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)
