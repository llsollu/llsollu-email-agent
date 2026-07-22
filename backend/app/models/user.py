import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    azure_oid: Mapped[str | None] = mapped_column(String(100), unique=True)
    department: Mapped[str | None] = mapped_column(String(120))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
