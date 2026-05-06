# Quiet Locker Router

A recruitment project built around the InPost parcel locker ecosystem.

The original assignment was intentionally open-ended, so instead of building a generic API wrapper, I focused on solving a concrete user problem:

> *"My preferred parcel locker is crowded or inconvenient. Which nearby alternative lockers can I realistically walk to?"*

This project turns raw locker availability data into actionable recommendations by combining parcel locker metadata, geographic calculations, walking routes, and map visualization.

The result is a lightweight web application that helps users discover nearby alternative lockers based on actual walking distance and walking time.

---

# Problem Definition

Instead of asking:

> "What data can I display?"

I asked:

> "What decision is the user trying to make?"

A user choosing a parcel locker usually does not care about raw API data. They care about:

- Is this locker convenient?
- If not, what are my alternatives?
- Can I actually walk there in a reasonable time?

That became the core product idea.

---

# What I Built

The application:

## 1. Loads parcel lockers from InPost API

At startup, the application downloads parcel locker data and filters locations in Warsaw.

Why Warsaw?

I deliberately narrowed the geographic scope to Warsaw — my home city and a place where I already had real usage scenarios in mind.

It also allowed me to:

- keep the dataset manageable,
- improve response times,

---

## 2. Suggests alternative lockers

When a user selects a locker, the system:

- reads InPost's recommended alternatives,
- resolves their coordinates,
- validates whether they are practical alternatives.

---

## 3. Calculates real walking routes

Instead of using straight-line distance only, the system calculates actual walking routes using OSRM.

This gives users:

- real walking distance,
- estimated walking time,
- route geometry for map visualization.

---

## 4. Filters unrealistic alternatives

Alternative lockers are only shown if they are realistically reachable:

- Maximum distance: **1200 meters**
- Maximum walking time: **10 minutes**

This prevents showing technically nearby (from the API) but practically useless recommendations.

---

# Features

- Parcel locker discovery
- Alternative locker recommendations
- Walking time estimation
- Route visualization on interactive map
- Frontend integration
- External API integration
- Error handling for incomplete or unavailable data

---

# Tech Stack

## Backend

- Python
- FastAPI
- Uvicorn
- HTTPX

## Frontend

- HTML
- JavaScript
- Leaflet.js

## External Services

- InPost API
- OSRM Routing API

---

# Project Structure

```bash
Inpost_task/
│
├── main.py                # Application entrypoint
│
├── services/
│   ├── inpost.py         # InPost API integration
│   └── routing.py        # Route and distance calculations
│
├── static/               # Frontend files
│
├── requirements.txt
└── README.md
```

---

# Installation

Clone the repository:

```bash
git clone https://github.com/wavyboyasf/Inpost_task.git
cd Inpost_task
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Running The Project

Start the application:

```bash
python main.py
```

# API Endpoints

## Get all lockers

```http
GET /api/lockers
```

Returns available parcel lockers used by the frontend.

---

## Get alternatives for selected locker

```http
GET /api/alternatives/{locker_name}
```

Returns:

- selected locker,
- recommended alternatives,
- walking distance,
- walking time,
- route geometry.

---

# Technical Decisions

## Why preload locker data on startup?

Instead of querying InPost API for every request, I preload locker data during application startup.

Benefits:

- lower latency,
- fewer external API calls,
- predictable performance.

This also makes the application more resilient if the external API becomes temporarily unavailable.

---

## Why use straight-line filtering before route calculation?

Route calculation requires external requests and is relatively expensive.

Before requesting a walking route, I first calculate geographic distance.

If a locker is obviously too far away, it gets rejected immediately.

Benefits:

- fewer network calls,
- faster responses,
- better scalability.

---

## Why not keep every experiment?

During development I experimented with additional APIs (for example public transport).

Some of these ideas had potential, but given the time constraints of the assignment, I made a deliberate product decision to focus on delivering a smaller, more reliable MVP.

Instead of expanding the scope with partially finished features, I prioritized the core experience and made sure the final version was stable, understandable, and production-ready.

---

# Error Handling

The application handles:

- invalid locker names,
- missing coordinates,
- unavailable external APIs,
- missing routing results,
- incomplete locker metadata.

Failures in individual requests do not crash the entire application.

---

# What I Wanted To Demonstrate

This project was designed to demonstrate more than coding ability.

I wanted to show:

## Clear communication

Taking an ambiguous task and turning it into a clearly defined product.

## Problem solving

Starting from user behavior instead of raw API data.

## Technical decision making

Making deliberate tradeoffs around:

- performance,
- API usage,
- architecture,
- reliability.

## Engineering ownership

Iterating, removing weak solutions, and shipping a cleaner final product instead of keeping every experiment.

---
# Future Improvements

Given more time, I would explore features that make the product feel more useful in everyday urban logistics:

- **Dynamic locker scoring** based on factors like walking distance, time of day, and locker popularity,
- **Transit-aware recommendations**, suggesting lockers near tram, metro, or bus connections,
- **Multi-city support**, validating whether the recommendation logic scales beyond Warsaw.
