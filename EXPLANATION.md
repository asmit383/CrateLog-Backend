# How It Works: The Fuel Optimization API

This project builds a smart route planner for trucks. It doesn't just find the way; it finds the cheapest way to buy gas along the journey. Here is the step-by-step process and the **code files** responsibly for each part.

## 1. The Request (**`core/views.py`**)
The process starts when you send a destination request to the API. The `RouteView` class in `views.py` acts as the traffic controller, receiving your input and coordinating all the other steps.
*   **Start**: "New York, NY"
*   **Finish**: "Los Angeles, CA"

## 2. Finding the Coordinates (**`core/data_manager.py`**)
Computers don't understand city names, they need numbers (Latitude and Longitude).
*   **The Code:** `CityGeocoder` class.
*   **What we do**: We look up the city names in a huge list of US cities (`us_cities.csv`) stored in memory.
*   **Result**: "New York" becomes `(40.71, -74.00)`.

## 3. Drawing the Route (**`core/routing.py`**)
Now we know where we start and end, but we need the actual road path.
*   **The Code:** `RouteService` class.
*   **Action**: We ask the **OSRM (Open Source Routing Machine)** service "How do I drive from A to B?".
*   **Result**: OSRM gives us:
    1.  The total distance (e.g., 2,800 miles).
    2.  The exact shape of the road (thousands of points used to draw the map).

## 4. The "Gas Station" Logic (**`core/optimizer.py`**)
This is the smartest part of the app.
*   **The Code:** `RouteOptimizer` class.
*   **Logic**:
    1.  The truck starts with a full tank (500 miles range).
    2.  It looks ahead along the route for the next 500 miles.
    3.  It finds **all the gas stations** in that range (using `FuelStationManager` in `data_manager.py`).
    4.  It picks the **cheapest one** to stop at (Greedy Algorithm).
    5.  It repeats this until the destination is reached.

*Note: We use a specialized "Spatial Tree" (KD-Tree) in `data_manager.py` to instantly find gas stations near the highway without checking every single station in the USA.*

## 5. The Response (**`core/views.py`**)
Finally, `views.py` bundles everything together and sends it back to you:
1.  **The Route**: The data needed to draw the blue line on a map.
2.  **The Stops**: A list of exactly where to stop, how much gas to buy, and the cost.
3.  **Total Cost**: The final price tag for the trip.

---
**Why is it fast?**
Instead of asking an external Google API 100 times "Is there a gas station here?", we loaded thousands of fuel prices into the server's memory when it started. This means the math happens instantly!
