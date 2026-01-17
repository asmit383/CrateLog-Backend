# Project Plan: Fuel Optimization Routing API

## 1. Objective
Build a Django-based API that calculates a route between two locations in the USA, identifies optimal fuel stops to minimize cost, and returns the route map (polyline), stops, and total fuel cost.

## 2. Constraints & Assumptions
- **Range**: 500 miles per tank.
- **Consumption**: 10 MPG.
- **Routing**: API must ideally use 1 call (minimized calls).
- **Fuel Data**: Provided via CSV (Needs to be uploaded).
- **Optimization Goal**: Minimize total fuel cost.
- **Tech Stack**: Django (latest), Python.

## 3. Architecture

### A. Endpoint
`POST /api/route/`

**Request Body** (JSON):
```json
{
  "start": "New York, NY",
  "finish": "Los Angeles, CA"
}
```

### B. Data & External Services
1.  **Routing/Map Service**:
    *   **Proposed Provider**: OpenRouteService (ORS) or OSRM (Open Source Routing Machine) via demo server.
    *   **Reason**: Generous free tier, returns detailed geometry (polyline) and distances.
    *   **Data Needed**: Total distance, route geometry (lat/lon points), sequential distance along route.
2.  **Fuel Data**:
    *   **Source**: User-provided CSV.
    *   **Processing**: In-memory loading (Pandas) or Import to Database (SQLite/PostgreSQL) with Geospatial indexing (GeoDjango) if complexity requires. Ideally, for a simple assignment, loading into a KD-Tree or simple list with bounding box filtering is sufficient.

### C. Core Logic (The "Gas Station Problem")
1.  **Geocoding**: Convert "Start" and "Finish" strings to coordinates (using the Routing API's geocoder).
2.  **Route Generation**: Fetch path from Start to Finish.
3.  **Station Filtering**:
    *   Identify fuel stations within a reasonable distance (e.g., 5-10 miles) of the route path.
    *   Project these stations onto the route to determine their "distance from start".
    *   Sort stations by distance from start.
4.  **Optimization Algorithm (Greedy approach)**:
    *   **State**: Current fuel ($F$), Current location ($D_{curr}$).
    *   **Goal**: Reach Destination ($D_{total}$).
    *   **Algorithm**:
        *   At current station $S_curr$, look at all reachable stations ($S_{next}$) within range ($R = 500 - (dist(S_{curr}, S_{next}))/MPG \times ...$ or simply map miles).
        *   **Case 1**: Minimum price within range is at current station.
            *   Fill up max (or enough to reach the next *cheaper* station beyond current range, but usually max is the safe greedy play if current is strictly cheapest).
        *   **Case 2**: There is a cheaper station reachable.
            *   Add just enough fuel to reach that cheaper station.
        *   **Case 3**: Destination is reachable without fueling.
            *   Don't fuel.
5.  **Output Construction**:
    *   Construct JSON response with route path, stops (lat/lon, name, price, gallons taken), and total cost.

## 4. Implementation Steps (Draft)
1.  **Setup Django**: Initialize project, create `api` app.
2.  **Ingest Data**: Create a script to read the fuel prices CSV.
3.  **Routing Service**: Implement `RoutingService` class to wrap OSRM/ORS calls.
4.  **Math/Geometry**: Implement distance calculations (Haversine) and point-to-line distance checks.
5.  **Optimizer**: Implement the fuel logic.
6.  **Views**: Connect inputs to the optimizer and return JSON.

## 5. Questions needed to proceed
- **Fuel Price CSV**: Please upload the attached file mentioned in the prompt.
- **Map Visualization**: Do you need a frontend map (Leaflet/Google Maps) or just the data for the map? (Prompt says "Return a map... Find a free API yourself for the map" -> Could mean an image or a tile layer URL, or just the Polyline for the frontend to render. Usually, returning the Polyline data is the modern API approach).
