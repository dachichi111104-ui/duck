from __future__ import annotations

import datetime as dt

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.config.constants import BarnStatus


class Barn(Base):
    __tablename__ = "barns"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    current_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=BarnStatus.ACTIVE)
    description: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    sync_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    last_modified_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    remote_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    flocks: Mapped[list["Flock"]] = relationship(back_populates="barn")

    @property
    def available_capacity(self) -> int:
        return max(self.capacity - self.current_count, 0)

    def __repr__(self) -> str:
        return f"<Barn {self.code}>"
