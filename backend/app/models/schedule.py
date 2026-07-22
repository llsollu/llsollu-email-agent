import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Schedule(Base, TimestampMixin):
    """시각 트리거. scheduler 디스패처가 next_run_at/enabled 기준으로 조회·재계산."""

    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cron: Mapped[str] = mapped_column(String(120), nullable=False)  # 표준 5필드 cron
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Seoul", nullable=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
