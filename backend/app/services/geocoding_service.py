"""
NameboardGeocodingService — derives lat/long, city, and state using Mappls (MapmyIndia).
Uses a tiered strategy: full address → pin code centroid → address only → not geocoded.
"""
from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import HTTPException

from app.config import get_settings

MAPPLS_TOKEN_URL = "https://outpost.mapmyindia.com/api/security/oauth/token"
MAPPLS_GEOCODE_URL = "https://atlas.mapmyindia.com/api/places/geocode"


@dataclass
class GeocodingResult:
    latitude: Optional[float]
    longitude: Optional[float]
    city: Optional[str]
    state: Optional[str]
    geocoding_status: str   # FULL_ADDRESS / PIN_CODE_CENTROID / ADDRESS_ONLY / NOT_GEOCODED
    geocoding_confidence: float


async def geocode(address: Optional[str], pin_code: Optional[str]) -> GeocodingResult:
    if not address and not pin_code:
        return GeocodingResult(
            latitude=None, longitude=None,
            city=None, state=None,
            geocoding_status="NOT_GEOCODED",
            geocoding_confidence=0.0,
        )

    token = await _get_mappls_token()

    if address and pin_code:
        result = await _geocode_full_address(token, address, pin_code)
        if result:
            return result

    if pin_code:
        result = await _geocode_pin_code(token, pin_code)
        if result:
            return result

    if address:
        result = await _geocode_address_only(token, address)
        if result:
            return result

    return GeocodingResult(
        latitude=None, longitude=None,
        city=None, state=None,
        geocoding_status="NOT_GEOCODED",
        geocoding_confidence=0.0,
    )


async def _get_mappls_token() -> str:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            MAPPLS_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.mappls_client_id,
                "client_secret": settings.mappls_client_secret,
            },
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Mappls auth failed: {response.text}")
    return response.json()["access_token"]


async def _geocode_full_address(token: str, address: str, pin_code: str) -> Optional[GeocodingResult]:
    result = await _call_geocode_api(token, f"{address} {pin_code}")
    if not result:
        return None

    lat, lng, city, state, returned_pin = result
    # Verify returned pin matches — if not, drop to lower-confidence strategy
    if returned_pin and returned_pin != pin_code:
        return None

    return GeocodingResult(
        latitude=lat, longitude=lng,
        city=city, state=state,
        geocoding_status="FULL_ADDRESS",
        geocoding_confidence=0.95,
    )


async def _geocode_pin_code(token: str, pin_code: str) -> Optional[GeocodingResult]:
    result = await _call_geocode_api(token, pin_code)
    if not result:
        return None
    lat, lng, city, state, _ = result
    return GeocodingResult(
        latitude=lat, longitude=lng,
        city=city, state=state,
        geocoding_status="PIN_CODE_CENTROID",
        geocoding_confidence=0.60,
    )


async def _geocode_address_only(token: str, address: str) -> Optional[GeocodingResult]:
    result = await _call_geocode_api(token, address)
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
    token: str, query: str
) -> Optional[tuple[float, float, Optional[str], Optional[str], Optional[str]]]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            MAPPLS_GEOCODE_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"address": query, "region": "IND"},
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
