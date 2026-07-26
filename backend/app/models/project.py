import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

PROJECT_STATUSES = ("storyboard", "active", "on_hold", "completed", "cancelled")


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
    category: Mapped[str | None] = mapped_column(String(80))  # 사용자 정의 분류
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    latest_update: Mapped[str | None] = mapped_column(Text)
    # 최근 메일 분석의 키워드 + 유사 키워드(검색 편의). mail_records.keywords 계승.
    keywords: Mapped[list | None] = mapped_column(JSON)
    # 카드=메일 이므로 발신인도 카드에 표시(mail_records 계승).
    from_name: Mapped[str | None] = mapped_column(String(200))
    from_address: Mapped[str | None] = mapped_column(String(320))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 최근 갱신을 유발한 원본 메일(mail_records.id). 상세 모달의 "원문 보기"에 사용.
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mail_records.id", ondelete="SET NULL")
    )
