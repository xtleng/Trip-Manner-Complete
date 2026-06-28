from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class MockRoute(Base):
    __tablename__ = "mock_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    scenario_index: Mapped[int] = mapped_column(Integer, default=0)
    plan_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # Full mock plan as JSON
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
