"""민감 설정(secret) 앱단 암호화. Fernet 대칭키 사용."""

import json

from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    if not settings.secret_enc_key:
        raise RuntimeError("SECRET_ENC_KEY 가 설정되지 않았습니다. `python -m app.tools.genkey` 로 생성하세요.")
    return Fernet(settings.secret_enc_key.encode())


def encrypt_secrets(data: dict) -> bytes:
    return _fernet().encrypt(json.dumps(data, ensure_ascii=False).encode("utf-8"))


def decrypt_secrets(blob: bytes | None) -> dict:
    if not blob:
        return {}
    return json.loads(_fernet().decrypt(blob).decode("utf-8"))


def generate_key() -> str:
    return Fernet.generate_key().decode()
