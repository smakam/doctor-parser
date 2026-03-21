"""
NameboardGeocodingService — derives lat/long, city, and state using Mappls (MapmyIndia).
Uses a tiered strategy: full address → pin code centroid → address only → not geocoded.

Auth: static API key passed as ?access_token= (Mappls new auth since Aug 2025).
"""
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import get_settings

MAPPLS_GEOCODE_URL = "https://atlas.mappls.com/api/places/geocode"


@dataclass
class GeocodingResult:
    latitude: Optional[float]
    longitude: Optional[float]
    city: Optional[str]
    state: Optional[str]
    geocoding_status: str   # FULL_ADDRESS / PIN_CODE_CENTROID / ADDRESS_ONLY / NOT_GEOCODED
    geocoding_confidence: float


async def geocode(address: Optional[str], pin_code: Optional[str]) -> GeocodingResult:
    _not_geocoded = GeocodingResult(
        latitude=None, longitude=None,
        city=None, state=None,
        geocoding_status="NOT_GEOCODED",
        geocoding_confidence=0.0,
    )

    if not address and not pin_code:
        return _not_geocoded

    settings = get_settings()
    if not settings.mappls_api_key:
        return _not_geocoded

    api_key = settings.mappls_api_key

    if address and pin_code:
        result = await _geocode_full_address(api_key, address, pin_code)
        if result:
            return result

    if pin_code:
        result = await _geocode_pin_code(api_key, pin_code)
        if result:
            return result

    if address:
        result = await _geocode_address_only(api_key, address)
        if result:
            return result

    return _not_geocoded


async def _geocode_full_address(api_key: str, address: str, pin_code: str) -> Optional[GeocodingResult]:
    result = await _call_geocode_api(api_key, f"{address} {pin_code}")
    if not result:
        return None

    lat, lng, city, state, returned_pin = result
    if returned_pin and returned_pin != pin_code:
        return None

    return GeocodingResult(
        latitude=lat, longitude=lng,
        city=city, state=state,
        geocoding_status="FULL_ADDRESS",
        geocoding_confidence=0.95,
    )


async def _geocode_pin_code(api_key: str, pin_code: str) -> Optional[GeocodingResult]:
    result = await _call_geocode_api(api_key, pin_code)
    if not result:
        return None
    lat, lng, city, state, _ = result
    return GeocodingResult(
        latitude=lat, longitude=lng,
        city=city, state=state,
        geocoding_status="PIN_CODE_CENTROID",
        geocoding_confidence=0.60,
    )


async def _geocode_address_only(api_key: str, address: str) -> Optional[GeocodingResult]:
    result = await _call_geocode_api(api_key, address)
    if not result:
        return None
    lat, lng, city, state, _ = result
    return GeocodingResult(
        latitude=lat, longitude=lng,
        city=city, state=state,
        geocoding_status="ADDRESS_ONLY",
        geocoding_confidence=0.50,
    )


async def _call_geocode_api(
    api_key: str, query: str
) -> Optional[tuple[float, float, Optional[str], Optional[str], Optional[str]]]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            MAPPLS_GEOCODE_URL,
            params={"address": query, "region": "IND", "access_token": api_key},
        )

    if response.status_code != 200:
        return None

    data = response.json()
    candidates = data.get("copResults", [])
    if not candidates:
        return None

    top = candidates[0]
    lat = float(top.get("latitude", 0) or 0)
    lng = float(top.get("longitude", 0) or 0)
    city = top.get("city") or top.get("district")
    state = top.get("state")
    pin = top.get("pincode")

    return lat, lng, city, state, pin
