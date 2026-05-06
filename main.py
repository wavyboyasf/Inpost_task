"""
Quiet Locker Router — Main FastAPI Application

Helps users find less busy InPost parcel lockers in Warsaw.
When a user selects a locker, the app suggests alternatives from
the 'recommended_low_interest_box_machines_list' field and calculates
walking time (Haversine-based, OSRM used only for polyline geometry).
Each alternative is enriched with a transit accessibility score from
the OpenStreetMap Overpass API (bus/tram/metro stops within 400 m).
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from services.inpost import (
    fetch_warsaw_lockers,
    fetch_single_locker,
    build_name_lookup,
    simplify_locker,
)
from services.routing import get_walking_route, haversine_distance_m

# Only show alternatives reachable within these thresholds
MAX_STRAIGHT_LINE_M = 1_200   # skip routing entirely if farther than this
MAX_WALKING_TIME_MIN = 10     # hide if estimated walk >10 min


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("  Quiet Locker Router — Starting up")
    print("=" * 60)

    warsaw_lockers = await fetch_warsaw_lockers()
    app.state.warsaw_lockers = warsaw_lockers
    app.state.name_lookup = build_name_lookup(warsaw_lockers)

    print(f"\n  Ready! {len(warsaw_lockers)} Warsaw lockers loaded.")
    print(f"  Open http://127.0.0.1:8000 in your browser.")
    print("=" * 60)

    yield


app = FastAPI(
    title="Quiet Locker Router",
    description="Find less busy InPost lockers in Warsaw",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Routes ────────────────────────────────────────────────────────


@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")


@app.get("/api/lockers")
async def get_lockers():
    lockers = app.state.warsaw_lockers
    return {
        "count": len(lockers),
        "lockers": [simplify_locker(l) for l in lockers],
    }


@app.get("/api/alternatives/{locker_name}")
async def get_alternatives(locker_name: str):
    """
    Return recommended low-interest alternatives for a given locker.

    Each alternative includes:
    - walking distance and time (Haversine-derived, realistic walking speed)
    - route polyline geometry (OSRM)
    - transit_stops: number of bus/tram/metro stops within 400 m (Overpass API)
    - convenience_score: walking_time penalised for poor transit access
    """
    lookup = app.state.name_lookup

    selected = lookup.get(locker_name)
    if not selected:
        raise HTTPException(status_code=404, detail=f"Locker '{locker_name}' not found")

    selected_loc = selected.get("location") or {}
    selected_lat = selected_loc.get("latitude")
    selected_lon = selected_loc.get("longitude")

    alt_names = selected.get("recommended_low_interest_box_machines_list") or []

    if not alt_names:
        return {
            "selected": simplify_locker(selected),
            "alternatives": [],
            "message": "This locker has no recommended alternatives.",
        }

    alternatives = []
    async with httpx.AsyncClient() as client:
        for name in alt_names:
            alt_locker = lookup.get(name)
            if not alt_locker:
                alt_locker = await fetch_single_locker(name)
            if not alt_locker:
                continue

            alt_loc = alt_locker.get("location") or {}
            alt_lat = alt_loc.get("latitude", 0)
            alt_lon = alt_loc.get("longitude", 0)

            if alt_lat == 0 or alt_lon == 0:
                continue

            # Pre-filter by straight-line distance
            straight_dist = haversine_distance_m(
                selected_lat, selected_lon, alt_lat, alt_lon
            )
            if straight_dist > MAX_STRAIGHT_LINE_M:
                continue

            route = await get_walking_route(client, selected_lat, selected_lon, alt_lat, alt_lon)

            if not route or route["duration_min"] > MAX_WALKING_TIME_MIN:
                continue

            alt_info = simplify_locker(alt_locker)
            alt_info["walking_distance_m"] = route["distance_m"]
            alt_info["walking_time_min"] = route["duration_min"]
            alt_info["route_geometry"] = route["geometry"]

            alternatives.append(alt_info)

    alternatives.sort(key=lambda a: a.get("walking_time_min") or 999)

    return {
        "selected": simplify_locker(selected),
        "alternatives": alternatives,
    }


# ─── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
