from __future__ import annotations

from pydantic import BaseModel, Field


class POI(BaseModel):
    """A single Point of Interest."""
    name: str
    latitude: float
    longitude: float
    category: str | None = None
    visit_duration_min: int | None = None
    description: str | None = None


class DayPlan(BaseModel):
    """One day within a multi-day route plan."""
    day: int
    pois: list[POI] = []
    transport_modes: list[str] = []
    notes: str | None = None


class RoutePlanResponse(BaseModel):
    """Full route plan returned to the frontend."""
    plan_id: str
    city: str
    algorithm: str | None = None
    days: list[DayPlan] = []
    total_cost_estimate: float | None = None
    summary: str | None = None


class RoutePlanRequest(BaseModel):
    """Request body for creating a route plan."""
    destination_city: str
    source_city: str | None = None
    days: int = Field(default=3, ge=1, le=14)
    preferences: dict | None = None
    budget: str | None = None  # "low" | "medium" | "high"
    travel_style: str | None = None
