import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# agent.status 값
AGENT_STATUSES = ("configuring", "active", "paused", "error")


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    template_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="configuring", nullable=False)
    error_detail: Mapped[str | None] = mapped_column(String(2000))

    # 비민감 설정
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # 민감 설정(암호화된 바이트). crypto.encrypt_secrets 로 저장.
    secrets_enc: Mapped[bytes | None] = mapped_column(LargeBinary)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
