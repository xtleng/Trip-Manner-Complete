from __future__ import annotations

import json
from pathlib import Path

# Base directory for mock data files
MOCK_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "mock"


def _load_json(file_path: Path) -> dict | list | None:
    """Safely load a JSON file, returning None if it does not exist."""
    if not file_path.exists():
        return None
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def get_mock_route(city: str, scenario_index: int = 0) -> dict | None:
    """Load a mock route plan for the given city.

    Mock files are expected at: data/mock/{city_slug}.json
    Each file should contain a list of scenario objects.

    Args:
        city: City name (case-insensitive).
        scenario_index: Index of the scenario variant to return.

    Returns:
        dict with mock route data, or None if no mock data exists.
    """
    city_slug = city.strip().lower().replace(" ", "_")
    file_path = MOCK_DATA_DIR / f"{city_slug}.json"

    data = _load_json(file_path)
    if data is None:
        # Return a generic stub if no file exists
        return {
            "city": city,
            "mock": True,
            "message": f"No mock data file found for '{city}'. Place a JSON file at {file_path}",
            "days": [],
        }

    if isinstance(data, list):
        idx = scenario_index % len(data) if data else 0
        return data[idx]

    return data


def list_available_mock_cities() -> list[str]:
    """Return a list of cities that have mock data files."""
    if not MOCK_DATA_DIR.exists():
        return []
    return [
        f.stem.replace("_", " ").title()
        for f in MOCK_DATA_DIR.glob("*.json")
    ]
