from __future__ import annotations

from pydantic import BaseModel


class MockStatusResponse(BaseModel):
    use_mock_data: bool


class MockStatusUpdate(BaseModel):
    use_mock_data: bool


class SupportedCity(BaseModel):
    name: str
    algorithms: list[str]
    country: str | None = None


class SupportedCitiesResponse(BaseModel):
    cities: list[SupportedCity]
