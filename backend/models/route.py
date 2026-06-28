from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    algorithm_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    query_input: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: the query quintuple
    route_result: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: POI sequence
    intent_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: intent visualization data
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
