from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class UserCheckin(Base):
    __tablename__ = "user_checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    poi_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("pois.id"), nullable=True)
    route_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("routes.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
