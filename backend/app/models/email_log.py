import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmailLog(Base):
    """T1: 처리한 수신 메일 로그."""

    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    message_id: Mapped[str | None] = mapped_column(String(400), index=True)
    subject: Mapped[str | None] = mapped_column(Text)
    from_address: Mapped[str | None] = mapped_column(String(320))
    client_name: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    action_required: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
