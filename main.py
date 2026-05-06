"""
Quiet Locker Router — Main FastAPI Application

Helps users find less busy InPost parcel lockers in Warsaw.
When a user selects a locker, the app suggests alternatives from
the 'recommended_low_interest_box_machines_list' field and calculates
walking time to each using OSRM pedestrian routing.
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
MAX_STRAIGHT_LINE_M = 1_200   # skip OSRM call entirely if farther than this
MAX_WALKING_TIME_MIN = 10     # hide alternative if OSRM says >10 min walk


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: fetch Warsaw lockers from InPost API (or cache),
    build the name lookup, and store everything in app.state.
    """
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

# Serve the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Routes ────────────────────────────────────────────────────────


@app.get("/")
async def serve_frontend():
    """Serve the main HTML page."""
    return FileResponse("static/index.html")


@app.get("/api/lockers")
async def get_lockers():
    """
    Return all Warsaw lockers with simplified data for map display.
    """
    lockers = app.state.warsaw_lockers
    return {
        "count": len(lockers),
        "lockers": [simplify_locker(l) for l in lockers],
    }


@app.get("/api/alternatives/{locker_name}")
async def get_alternatives(locker_name: str):
    """
    For a given locker, return its recommended low-interest alternatives
    with walking distance and time calculated via OSRM.
    """
    lookup = app.state.name_lookup

    # Find the selected locker
    selected = lookup.get(locker_name)
    if not selected:
        raise HTTPException(status_code=404, detail=f"Locker '{locker_name}' not found")

    selected_loc = selected.get("location") or {}
    selected_lat = selected_loc.get("latitude")
    selected_lon = selected_loc.get("longitude")

    # Get alternative names
    alt_names = selected.get("recommended_low_interest_box_machines_list") or []

    if not alt_names:
        return {
            "selected": simplify_locker(selected),
            "alternatives": [],
            "message": "This locker has no recommended alternatives.",
        }

    # Resolve each alternative and calculate walking routes
    alternatives = []
    async with httpx.AsyncClient() as client:
        for name in alt_names:
            # Try our Warsaw lookup first, then fetch individually
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

            # Pre-filter: skip OSRM call if locker is too far in straight line
            straight_dist = haversine_distance_m(
                selected_lat, selected_lon, alt_lat, alt_lon
            )
            if straight_dist > MAX_STRAIGHT_LINE_M:
                continue

            # Calculate walking route
            route = await get_walking_route(
                client, selected_lat, selected_lon, alt_lat, alt_lon
            )

            # Post-filter: discard if walking time exceeds threshold
            if not route or route["duration_min"] > MAX_WALKING_TIME_MIN:
                continue

            alt_info = simplify_locker(alt_locker)
            alt_info["walking_distance_m"] = route["distance_m"]
            alt_info["walking_time_min"] = route["duration_min"]
            alt_info["route_geometry"] = route["geometry"]

            alternatives.append(alt_info)

    # Sort by walking time (closest first)
    alternatives.sort(key=lambda a: a.get("walking_time_min") or 999)

    return {
        "selected": simplify_locker(selected),
        "alternatives": alternatives,
    }


# ─── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
