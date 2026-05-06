"""
Walking route calculation service.

Time and distance are calculated from Haversine (straight-line × 1.35 street
factor, at 5 km/h walking speed). The public OSRM demo server returns car
speeds (~32 km/h) for both /foot/ and /driving/ profiles, so its duration
field is not usable. OSRM is kept only to obtain the route polyline geometry
for map display.
"""

import httpx
import asyncio
import math

OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"

_WALKING_SPEED_M_PER_MIN = 5_000 / 60   # 5 km/h in m/min
_STREET_FACTOR = 1.35                    # straight-line → actual street distance

# Rate limiting: max 2 concurrent OSRM requests, 200ms delay between them
_semaphore = asyncio.Semaphore(2)

# Simple in-memory cache: (from_coords, to_coords) -> result
_route_cache: dict[tuple, dict] = {}


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance between two lat/lon points in meters."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _walking_metrics(straight_m: float) -> tuple[int, float]:
    """Return (estimated_street_distance_m, walking_time_min) from Haversine distance."""
    street_m = round(straight_m * _STREET_FACTOR)
    time_min = round(street_m / _WALKING_SPEED_M_PER_MIN, 1)
    return street_m, time_min


async def get_walking_route(
    client: httpx.AsyncClient,
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
) -> dict | None:
    """
    Return walking metrics between two points.

    Distance and time are derived from Haversine + walking-speed formula
    (OSRM public demo uses car speeds regardless of profile). OSRM is called
    only to get the route polyline geometry for map display.

    Returns dict with:
        - distance_m: estimated walking distance in meters
        - duration_s: estimated walking time in seconds
        - duration_min: estimated walking time in minutes (rounded to 1 dp)
        - geometry: GeoJSON LineString from OSRM (may be None if OSRM fails)
    """
    cache_key = (round(from_lat, 5), round(from_lon, 5),
                 round(to_lat, 5), round(to_lon, 5))
    if cache_key in _route_cache:
        return _route_cache[cache_key]

    straight_m = haversine_distance_m(from_lat, from_lon, to_lat, to_lon)
    street_m, time_min = _walking_metrics(straight_m)

    # Fetch geometry from OSRM (driving profile — only used for drawing the polyline)
    geometry = None
    coords = f"{from_lon},{from_lat};{to_lon},{to_lat}"
    url = f"{OSRM_BASE}/{coords}"

    async with _semaphore:
        try:
            response = await client.get(
                url,
                params={"overview": "full", "geometries": "geojson"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") == "Ok" and data.get("routes"):
                geometry = data["routes"][0]["geometry"]

            await asyncio.sleep(0.2)

        except Exception as e:
            print(f"[OSRM] Geometry fetch failed: {e}")

    result = {
        "distance_m": street_m,
        "duration_s": round(time_min * 60),
        "duration_min": time_min,
        "geometry": geometry,
    }

    _route_cache[cache_key] = result
    return result
