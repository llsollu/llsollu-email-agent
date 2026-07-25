import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MailRecord(Base, TimestampMixin):
    """메일함 단위로 공유되는 원문 + LLM 분석 결과.

    수신형 에이전트(이슈 관리·타임라인)들이 (mailbox, message_id) 로 공유·재사용한다.
    분석은 메일함당 1회만 수행(캐시). 카테고리도 여기 저장되어 에이전트 간 공유된다.
    """

    __tablename__ = "mail_records"
    __table_args__ = (UniqueConstraint("mailbox", "message_id", name="uq_mail_mailbox_msg"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    mailbox: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    message_id: Mapped[str] = mapped_column(String(400), nullable=False)

    # 원문
    subject: Mapped[str | None] = mapped_column(Text)
    from_address: Mapped[str | None] = mapped_column(String(320))
    from_name: Mapped[str | None] = mapped_column(String(200))
    direction: Mapped[str] = mapped_column(String(8), default="in")  # in|out
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    body_text: Mapped[str | None] = mapped_column(Text)

    # 공유 분석 결과
    client_name: Mapped[str | None] = mapped_column(String(200))
    project_title: Mapped[str | None] = mapped_column(String(400))
    category: Mapped[str | None] = mapped_column(String(80))
    summary: Mapped[str | None] = mapped_column(Text)
    action_required: Mapped[bool] = mapped_column(Boolean, default=False)
    issue: Mapped[dict | None] = mapped_column(JSON)
    points: Mapped[list | None] = mapped_column(JSON)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    analyzer_version: Mapped[str | None] = mapped_column(String(20))
