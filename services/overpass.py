"""
OpenStreetMap Overpass API — public transit stop lookup.

Counts bus, tram, and metro stops within a given radius of a point.
No API key required. Used to score locker accessibility by public transport.
"""

import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

_cache: dict[tuple, int] = {}


async def transit_stops_nearby(
    lat: float,
    lon: float,
    radius_m: int = 400,
) -> int:
    """
    Return the number of public transit stops within radius_m metres of (lat, lon).
    Counts bus stops, tram stops, and metro entrances from OpenStreetMap data.
    Returns 0 on any error so it never blocks the main response.
    Uses its own httpx client to avoid header pollution from the shared OSRM client.
    """
    cache_key = (round(lat, 4), round(lon, 4), radius_m)
    if cache_key in _cache:
        return _cache[cache_key]

    query = (
        f"[out:json][timeout:6];"
        f"("
        f'node["highway"="bus_stop"](around:{radius_m},{lat},{lon});'
        f'node["railway"="tram_stop"](around:{radius_m},{lat},{lon});'
        f'node["railway"="subway_entrance"](around:{radius_m},{lat},{lon});'
        f'node["public_transport"="stop_position"]["bus"="yes"](around:{radius_m},{lat},{lon});'
        f'node["public_transport"="stop_position"]["tram"="yes"](around:{radius_m},{lat},{lon});'
        f");out count;"
    )

    count = 0
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                OVERPASS_URL,
                params={"data": query},
                headers={"Accept": "*/*"},
                timeout=8.0,
            )
            response.raise_for_status()
            elements = response.json().get("elements", [])
            if elements and elements[0].get("type") == "count":
                count = int(elements[0]["tags"].get("total", 0))
    except Exception as e:
        print(f"[Overpass] Failed for ({lat:.4f},{lon:.4f}): {e}")

    _cache[cache_key] = count
    return count
