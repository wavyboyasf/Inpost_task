# Quiet Locker Router

A recruitment project built around the InPost locker ecosystem.

The application helps users find alternative parcel lockers in Warsaw when their preferred locker is highly occupied or less convenient.

Instead of only showing locker availability, the app analyzes recommended alternative lockers and filters them based on **real walking distance and estimated walking time**, giving users practical nearby options.

---

# Problem Definition

The original task was intentionally open-ended, so I narrowed it down into a specific user problem:

> *"I want to send or collect a parcel, but my preferred locker is crowded or inconvenient. What nearby alternatives can I realistically walk to?"*

To solve this, I built an API + lightweight frontend that:

- Fetches locker data from InPost
- Identifies lockers in Warsaw
- Finds recommended alternative lockers
- Calculates actual walking routes between lockers
- Filters out alternatives that are too far to be useful

The goal was not only to present data, but to provide **actionable recommendations**.

---

# Features

## Locker Discovery

- Loads all Warsaw lockers at application startup
- Creates an in-memory lookup for fast access

## Alternative Suggestions

When a locker is selected, the application:

- Reads `recommended_low_interest_box_machines_list`
- Resolves recommended locker data
- Calculates walking routes using OSRM

## Smart Filtering

Alternatives are shown only if they are practical:

- Distance ≤ **1200m**
- Walking time ≤ **10 minutes**

This avoids unnecessary API calls and irrelevant recommendations.

## Route Visualization

Each result contains route geometry that can be visualized on a map.

---

# Tech Stack

## Backend

- Python
- FastAPI
- Uvicorn
- HTTPX

## External APIs

- InPost API
- OSRM Routing API

## Frontend

- HTML
- JavaScript
- Static assets served by FastAPI

---

# Project Structure

```bash
Inpost_task/
│
├── main.py                 # Application entrypoint
├── services/
│   ├── inpost.py          # InPost API integration
│   └── routing.py         # Distance + route calculations
│
├── static/                # Frontend assets
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

# Running the Application

Run the server:

```bash
python main.py
```

or:

```bash
uvicorn main:app --reload
```

Application will be available at:

```bash
http://127.0.0.1:8000
```

---

# API Endpoints

## Get all lockers

```http
GET /api/lockers
```

Returns:

- Total locker count
- Basic locker information

---

## Get alternative lockers

```http
GET /api/alternatives/{locker_name}
```

Returns:

- Selected locker
- Nearby alternatives
- Walking distance
- Estimated walking time
- Route geometry

---

# Technical Decisions

## Why preload locker data on startup?

Instead of requesting locker data on every API call, the application loads all Warsaw lockers once during startup.

Benefits:

- Faster response times
- Reduced dependency on external APIs
- Better user experience

---

## Why filter by straight-line distance first?

Route calculations require external requests and are more expensive.

Using a preliminary geographic distance check helps eliminate lockers that are obviously too far away.

Benefits:

- Lower API usage
- Faster processing
- Better scalability

---

## Why async architecture?

Both InPost and routing APIs are I/O-bound operations.

Using asynchronous requests keeps the application responsive even when multiple external calls are needed.

---

# Error Handling

The application handles:

- Invalid locker names (`404`)
- Missing location data
- External API failures
- Missing route results

Fallback logic ensures partial failures do not break the application.

---

# Possible Improvements

If I had more time, I would add:

- Unit and integration tests
- Docker containerization
- Redis caching
- Interactive frontend map
- CI/CD pipeline
- Search and filtering in UI

---

# What I Wanted to Demonstrate

This project was designed to demonstrate:

- Turning an ambiguous task into a concrete product problem
- Clean project structure
- Practical API integrations
- Performance-oriented engineering decisions
- User-focused product thinking
