from __future__ import annotations

from fastapi import APIRouter

from config import settings
from schemas.config_schema import (
    MockStatusResponse,
    MockStatusUpdate,
    SupportedCitiesResponse,
    SupportedCity,
)

router = APIRouter(prefix="/config", tags=["config"])

# ---------------------------------------------------------------------------
# Supported cities registry
# ---------------------------------------------------------------------------
SUPPORTED_CITIES: list[SupportedCity] = [
    SupportedCity(name="Glasgow", algorithms=["ekd_trip"], country="UK"),
    SupportedCity(name="Osaka", algorithms=["ekd_trip"], country="Japan"),
    SupportedCity(name="Toronto", algorithms=["ekd_trip"], country="Canada"),
    SupportedCity(name="Tokyo", algorithms=["ekd_trip"], country="Japan"),
    SupportedCity(name="New York", algorithms=["cross_city"], country="USA"),
    SupportedCity(name="Los Angeles", algorithms=["cross_city"], country="USA"),
    SupportedCity(name="San Francisco", algorithms=["cross_city"], country="USA"),
]


@router.get("/mock-status", response_model=MockStatusResponse)
async def get_mock_status():
    return MockStatusResponse(use_mock_data=settings.USE_MOCK_DATA)


@router.put("/mock-status", response_model=MockStatusResponse)
async def set_mock_status(body: MockStatusUpdate):
    settings.USE_MOCK_DATA = body.use_mock_data
    return MockStatusResponse(use_mock_data=settings.USE_MOCK_DATA)


@router.get("/supported-cities", response_model=SupportedCitiesResponse)
async def get_supported_cities():
    return SupportedCitiesResponse(cities=SUPPORTED_CITIES)
