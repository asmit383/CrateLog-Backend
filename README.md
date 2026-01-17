# Fuel Optimization API

## Overview
A Django-based API that calculates the optimal route between two US cities for a truck, identifying the most cost-effective fuel stops along the way.

## Features
- **Route Planning**: Uses OSRM (Open Source Routing Machine) to generate route geometry and distance.
- **Fuel Optimization**: Implements a "Gas Station Problem" greedy algorithm to minimize fuel costs based on vehicle range and live fuel prices.
- **Smart Geocoding**: Resolves US Cities to coordinates internally without external API limits.
- **Detailed Output**: Returns full route geometry (LineString), stop locations, price per gallon, and total trip cost.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/asmit383/CrateLog-Backend.git
    cd CrateLog-Backend
    ```

2.  **Create and Activate Virtual Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run Migrations**:
    ```bash
    python manage.py migrate
    ```

5.  **Start Server**:
    ```bash
    python manage.py runserver
    ```

## Usage

**Endpoint**: `POST /api/route/`

**Request Body**:
```json
{
  "start": "New York, NY",
  "finish": "Los Angeles, CA",
  "return_map": true
}
```

*   `start`: Origin city (e.g., "City, StateCode" or "City, StateName").
*   `finish`: Destination city.
*   `return_map`: (Optional) Boolean. Set to `false` if you only want the table of stops without the huge map geometry.

**Response Example**:
```json
{
  "route": {
    "start": "New York, NY",
    "finish": "Los Angeles, CA",
    "distance_miles": 2800.26,
    "map_geometry": { ... }
  },
  "fuel_stops": [
    {
      "city": "NORTH JACKSON",
      "name": "SHEETZ #791",
      "price": 3.06,
      "cost_chunk": 122.65
    },
    ...
  ],
  "total_fuel_cost": 768.32
}
```
