from __future__ import annotations

# Cities supported by the EKD-Trip algorithm
EKD_TRIP_CITIES: set[str] = {"glasgow", "osaka", "toronto", "tokyo"}

# Cities supported by the Cross-City algorithm
CROSS_CITY_CITIES: set[str] = {"new york", "los angeles", "san francisco"}


def determine_algorithm(destination_city: str, source_city: str | None = None) -> str:
    """Decide which route-planning algorithm to use based on the destination city.

    Returns one of: "ekd_trip", "cross_city", or "llm_only".
    """
    city_lower = destination_city.strip().lower()

    if city_lower in EKD_TRIP_CITIES:
        return "ekd_trip"

    if city_lower in CROSS_CITY_CITIES:
        return "cross_city"

    # Fallback: use LLM-only planning for cities not covered by specialised algorithms
    return "llm_only"
