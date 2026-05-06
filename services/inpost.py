"""
InPost API data fetching and filtering service.

Handles pagination through the InPost Points API,
filters lockers by city (Warsaw), and provides fast
name-based lookups for alternative locker resolution.
"""

import httpx
import asyncio
import json
from pathlib import Path

INPOST_API_BASE = "https://api-global-points.easypack24.net/v1/points"
CACHE_FILE = Path("data/warsaw_lockers.json")
PER_PAGE = 500
MAX_CONCURRENCY = 10


async def _fetch_page(
    client: httpx.AsyncClient,
    page: int,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Fetch a single page from InPost API with concurrency control."""
    async with semaphore:
        response = await client.get(
            INPOST_API_BASE,
            params={"page": page, "per_page": PER_PAGE},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json().get("items", [])


def _is_warsaw_operating(locker: dict) -> bool:
    """Check if a locker is in Warsaw, operating, and has valid coordinates."""
    address = locker.get("address_details") or {}
    city = address.get("city", "")
    status = locker.get("status", "")
    location = locker.get("location") or {}
    lat = location.get("latitude", 0)
    lon = location.get("longitude", 0)

    return "Warszawa" in city and status == "Operating" and lat != 0 and lon != 0


async def fetch_warsaw_lockers() -> list[dict]:
    """
    Fetch all InPost lockers, filter for Warsaw, and cache results.

    On first run, paginates through the entire InPost API (~300 pages)
    and keeps only Warsaw lockers. Saves to a JSON cache file so
    subsequent startups are instant.
    """
    # Fast path: load from cache
    if CACHE_FILE.exists():
        print(f"[InPost] Loading cached Warsaw data from {CACHE_FILE}")
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            lockers = json.load(f)
        print(f"[InPost] Loaded {len(lockers)} Warsaw lockers from cache")
        return lockers

    print("[InPost] No cache found. Fetching all lockers from API...")
    warsaw_lockers = []

    async with httpx.AsyncClient() as client:
        # First request — get total number of pages
        first_resp = await client.get(
            INPOST_API_BASE,
            params={"page": 1, "per_page": PER_PAGE},
            timeout=30.0,
        )
        first_resp.raise_for_status()
        first_data = first_resp.json()

        total_pages = first_data.get("total_pages", 1)
        total_count = first_data.get("count", 0)
        print(f"[InPost] Total lockers: {total_count}, pages: {total_pages}")

        # Process first page
        for item in first_data.get("items", []):
            if _is_warsaw_operating(item):
                warsaw_lockers.append(item)

        # Fetch remaining pages concurrently
        semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        tasks = [
            _fetch_page(client, page, semaphore)
            for page in range(2, total_pages + 1)
        ]

        done_count = 1
        for coro in asyncio.as_completed(tasks):
            try:
                items = await coro
                for item in items:
                    if _is_warsaw_operating(item):
                        warsaw_lockers.append(item)
            except Exception as e:
                print(f"[InPost] Error fetching page: {e}")

            done_count += 1
            if done_count % 50 == 0 or done_count == total_pages:
                print(
                    f"[InPost] Progress: {done_count}/{total_pages} pages, "
                    f"found {len(warsaw_lockers)} Warsaw lockers"
                )

    print(f"[InPost] Done! Found {len(warsaw_lockers)} Warsaw lockers total")

    # Cache to disk
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(warsaw_lockers, f, ensure_ascii=False)
    print(f"[InPost] Cached to {CACHE_FILE}")

    return warsaw_lockers


async def fetch_single_locker(name: str) -> dict | None:
    """
    Fetch a single locker by name from InPost API.

    Used to resolve alternative lockers that are outside Warsaw
    (not in our cached dataset).
    """
    url = f"{INPOST_API_BASE}/PL/{name}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"[InPost] Failed to fetch locker {name}: {e}")
    return None


def build_name_lookup(lockers: list[dict]) -> dict[str, dict]:
    """Build a {name: locker_data} dict for O(1) lookups."""
    return {locker["name"]: locker for locker in lockers}


def simplify_locker(locker: dict) -> dict:
    """Extract only the fields needed by the frontend."""
    location = locker.get("location") or {}
    address = locker.get("address_details") or {}
    alternatives = locker.get("recommended_low_interest_box_machines_list") or []

    return {
        "name": locker.get("name"),
        "lat": location.get("latitude"),
        "lon": location.get("longitude"),
        "address": f"{address.get('street', '')} {address.get('building_number', '')}".strip(),
        "city": address.get("city", ""),
        "post_code": address.get("post_code", ""),
        "status": locker.get("status"),
        "location_description": locker.get("location_description"),
        "physical_type": locker.get("physical_type"),
        "easy_access_zone": locker.get("easy_access_zone"),
        "has_alternatives": len(alternatives) > 0,
        "alternatives_count": len(alternatives),
        "image_url": locker.get("image_url"),
        "opening_hours": locker.get("opening_hours"),
        "is_247": locker.get("location_247", False),
        "air_index_level": locker.get("air_index_level"),
        "location_type": locker.get("location_type"),
    }
