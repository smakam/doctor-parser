"""
NameboardGeocodingService — derives lat/long, city, and state using Google Maps Geocoding API.
Uses a tiered strategy: full address → pin code centroid → address only → not geocoded.
"""

from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import get_settings

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@dataclass
class GeocodingResult:
    latitude: Optional[float]
    longitude: Optional[float]
    city: Optional[str]
    state: Optional[str]
    geocoding_status: (
        str  # FULL_ADDRESS / PIN_CODE_CENTROID / ADDRESS_ONLY / NOT_GEOCODED
    )
    geocoding_confidence: float


async def geocode(address: Optional[str], pin_code: Optional[str]) -> GeocodingResult:
    _not_geocoded = GeocodingResult(
        latitude=None,
        longitude=None,
        city=None,
        state=None,
        geocoding_status="NOT_GEOCODED",
        geocoding_confidence=0.0,
    )

    if not address and not pin_code:
        return _not_geocoded

    settings = get_settings()
    api_key = settings.google_vision_api_key  # same GCP key works for Geocoding API

    if address and pin_code:
        result = await _call_geocode_api(
            api_key, f"{address} {pin_code}", "FULL_ADDRESS", 0.95
        )
        if result:
            return result

    if pin_code:
        result = await _call_geocode_api(
            api_key, f"{pin_code} India", "PIN_CODE_CENTROID", 0.60
        )
        if result:
            return result

    if address:
        result = await _call_geocode_api(api_key, address, "ADDRESS_ONLY", 0.50)
        if result:
            return result

    return _not_geocoded


async def _call_geocode_api(
    api_key: str,
    query: str,
    status: str,
    confidence: float,
) -> Optional[GeocodingResult]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            GOOGLE_GEOCODE_URL,
            params={"address": query, "region": "IN", "key": api_key},
        )

    if response.status_code != 200:
        return None

    data = response.json()
    results = data.get("results", [])
    if not results or data.get("status") not in ("OK", "ZERO_RESULTS"):
        return None
    if not results:
        return None

    top = results[0]
    location = top.get("geometry", {}).get("location", {})
    lat = location.get("lat")
    lng = location.get("lng")
    if not lat or not lng:
        return None

    city = None
    state = None
    for component in top.get("address_components", []):
        types = component.get("types", [])
        if "locality" in types:
            city = component["long_name"]
        elif "administrative_area_level_1" in types:
            state = component["long_name"]

    return GeocodingResult(
        latitude=lat,
        longitude=lng,
        city=city,
        state=state,
        geocoding_status=status,
        geocoding_confidence=confidence,
    )
