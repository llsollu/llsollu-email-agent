import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

PROJECT_STATUSES = ("active", "on_hold", "completed", "cancelled")


class Project(Base, TimestampMixin):
    """T1(project_tracker) 도메인. agent_id로 스코프."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    client_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    phase: Mapped[str | None] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    latest_update: Mapped[str | None] = mapped_column(Text)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
