import numpy as np
import pandas as pd
from .data_manager import FuelStationManager
from geopy.distance import geodesic

class RouteOptimizer:
    def __init__(self, route_data):
        raw_points = route_data['path']
        # Downsample to speed up initialization and searching
        # Keep first and last, sample every 10th in between
        if len(raw_points) > 1000:
            self.route_points = [raw_points[0]] + raw_points[1:-1:10] + [raw_points[-1]]
        else:
            self.route_points = raw_points
            
        self.total_distance = route_data['distance_miles']
        self.manager = FuelStationManager.get_instance()
        
        self.cum_dist = [0]
        cur = 0
        for i in range(1, len(self.route_points)):
            # Dist between i-1 and i
            d = geodesic(self.route_points[i-1], self.route_points[i]).miles
            cur += d
            self.cum_dist.append(cur)
        
        self.cum_dist = np.array(self.cum_dist)
        
        # Normalize to match OSRM total distance
        if cur > 0:
            scale = self.total_distance / cur
            self.cum_dist = self.cum_dist * scale
            
    def optimize(self):
        stops = []
        total_fuel_cost = 0
        
        # Simulation State
        current_route_idx = 0
        current_tank_range = 500 # Start full
        tank_capacity_range = 500
        total_dist = self.cum_dist[-1]
        
        # While we cannot reach the end
        while (self.cum_dist[current_route_idx] + current_tank_range) < total_dist:
            
            # Defines the window of "reachable" route indices
            current_dist = self.cum_dist[current_route_idx]
            max_reachable_dist = current_dist + current_tank_range
            
            # Constraints:
            # We must stop before we run out of fuel.
            # Best strategy: Look at all stations reachable.
            #   Find cheapest station.
            #   But wait, if the cheapest station is at mile 10, and we have 500 miles range, 
            #   stopping there wastes our range if there is a "reasonably priced" station at mile 450.
            #   Actually, Cost = Price * Gallons. 
            #   Minimizing cost technically means buying *cheap fuel*.
            #   If mile 10 is $1/gal and mile 450 is $5/gal, we SHOULD fill at mile 10?
            #   No, we are full at mile 0. We can only top up 1 gallon at mile 10.
            #   So we can't really capitalize on it unless we arrive empty.
            
            # REALISTIC STRATEGY (Greedy with Buffer):
            # Drive as far as possible? 
            # To minimize price paid, we want to buy fuel at lowest price stations.
            # Since we start full, we only buy what we burn.
            # So, the cost of the *segment* is determined by the price at the *end* of the segment (where we refill).
            # Therefore, to minimize cost, we should target the Refuel Station with the Lowest Price
            # within the [Minimum Reachable, Maximum Reachable] window?
            # Actually, just finding the cheapest station in the reachable window is the standard approach.
            
            # Define window:
            # Start: current_route_idx + 1 (Look ahead)
            # End: index where dist > max_reachable_dist
            
            search_start_idx = current_route_idx + 1
            # Find index strictly less than max reachable (minus a buffer for safety, say 10 miles)
            safe_max_dist = max_reachable_dist - 10
            
            # Numpy searchsorted to find boundary
            search_end_idx = np.searchsorted(self.cum_dist, safe_max_dist, side='right') - 1
            
            if search_end_idx <= search_start_idx:
                # Should not happen unless steps are huge or stuck
                raise Exception("No progress possible - stuck at location.")
            
            # Scan for stations along this segment
            # Sampling to avoid checking every point
            # Sample every ~20th point or ~5 miles?
            # Step size based on array size
            step = max(1, (search_end_idx - search_start_idx) // 20) 
            
            candidates = []
            
            for i in range(search_start_idx, search_end_idx + 1, step): 
                # Optimization: Skip points too close to current location (prevent 0-progress loops)
                if (self.cum_dist[i] - self.cum_dist[current_route_idx]) < 15:
                    continue

                pt = self.route_points[i]
                lat, lon = pt
                # Search stations within 10 miles (approx 0.15 deg)
                nearby = self.manager.find_nearby_stations(lat, lon, radius_deg=0.15)
                
                if not nearby.empty:
                    # Calculate exact distance from start for each station (projection)
                    # Simple approx: assume it's at self.cum_dist[i]
                    # Better: Re-calc geodesic
                    for _, station in nearby.iterrows():
                        candidates.append({
                            'station': station,
                            'route_idx': i,
                            'price': station['price'],
                            'lat': station['lat'],
                            'lon': station['lon']
                        })
            
            if not candidates:
                # Emergency extend search?
                # Or just Fail
                return {"error": "No fuel stations found within range."}
            
            # Logic: Find Cheapest. 
            # Tie-break: Furthest along route (maximize i).
            best_stop = sorted(candidates, key=lambda x: (x['price'], -x['route_idx']))[0]
            
            # Execute Stop
            stop_station = best_stop['station']
            stop_idx = best_stop['route_idx']
            
            # Calculate Fuel Consumed to get here
            # dist_driven = self.cum_dist[stop_idx] - self.cum_dist[current_route_idx]
            # gallons_used = dist_driven / 10.0
            
            # Wait, cost calculation:
            # Return "Total money spent on fuel".
            # We arrive at Stop. We Refill. 
            # How much do we refill? To Full?
            # Yes, refill to full.
            # Cost = gallons_used * stop_station['price']
            
            # Wait, if we stop at Mile 100 (Price $4), and then Mile 600 (Price $2).
            # We pay for the first 100 miles at $4/gal.
            # We pay for the next 500 miles at $2/gal.
            # So yes, logic holds: The price of the station pays for the segment *preceding* it.
            # So minimizing the price of the Chosen Station minimizes the cost of the Previous Segment.
            # BUT, we can't choose the *previous* segment length easily?
            # Actually we can.
            # If we stretch the previous segment (drive further), we pay the price of the *destination* station for more miles.
            # If the destination station is Cheap, we want to drive AS FAR AS POSSIBLE to get there?
            # No, if the destination station is Cheap, we pay that Cheap rate for all miles driven to get there.
            # So yes: If Next_Station is Cheap -> Maximize Distance to it.
            # If Next_Station is Expensive -> Minimized Distance?
            # No, you HAVE to stop there to refill.
            # So you are paying Expensive_Rate * Distance_Driven.
            # So if you *must* stop at an expensive station, you want to drive as *little* as possible to get there?
            # Logic Loop:
            # 1. Start Loop.
            # 2. Look ahead.
            # 3. If there is a "Super Cheap" station at limit of range -> Drive there. (We pay Cheap_Rate * 500 miles? No!)
            
            # CORRECT COST LOGIC:
            # You fill up AT the station.
            # You pay: (Gallons Put In) * Price.
            # Gallons Put In = (Capacity - Current_Level).
            # Current_Level = Capacity - (Distance Driven / MPG).
            # So Gallons Put In = Distance Driven / MPG.
            # So Cost = (Distance Driven / 10) * Price_At_Station.
            # Therefore: The cost of the leg IS determined by the Price at the END of the leg.
            # Conclusion: We want to target the CHEAPEST station. Matches intuition.
            
            dist_leg = self.cum_dist[stop_idx] - self.cum_dist[current_route_idx]
            gallons_filled = dist_leg / 10.0
            cost = gallons_filled * float(stop_station['price'])
            
            total_fuel_cost += cost
            stops.append({
                "city": stop_station['City_Norm'], # or name?
                "name": stop_station['name'],
                "address": stop_station['address'],
                "lat": stop_station['lat'],
                "lon": stop_station['lon'],
                "price": float(stop_station['price']),
                "gallons": round(gallons_filled, 2),
                "cost_chunk": round(cost, 2)
            })
            
            # Update state
            current_route_idx = stop_idx
            # Tank is now full
            current_tank_range = 500
        
        # Finally, reach destination?
        # The while loop breaks when (current + 500) >= total.
        # Implies we can drive to finish.
        # Do we pay for the fuel used on the last leg?
        # "Total money spent on fuel".
        # Assuming we return the truck empty? Or just the cost to perform the trip?
        # If we don't refill at destination, the cost technically isn't "Spent" at a pump.
        # But for the purpose of the API "Fuel Cost of Trip", we should include the value of fuel consumed.
        # I will add a "Phantom Refill" at destination or just add the cost based on Average?
        # User prompt: "Optimal location to fuel up... return total money spent".
        # Usually implies actual transaction cost.
        # If I don't fill at the end, Total Cost = sum of intermediate stops.
        # Example: Trip 400 miles. Apps says "Stops: 0, Cost: $0".
        # User might think "Free trip!".
        # I will document this behavior: "Cost represents fuel purchased at stops. Estimates does not include final tank burn if no refill required."
        # OR: I can assume a refill at destination is required to return vehicle to "Full".
        # That is the standard rental car rule. Return Full.
        # Let's Implement **Return Full**.
        # It makes the cost comparison fair.
        
        final_leg_dist = total_dist - self.cum_dist[current_route_idx]
        # We need to price this leg.
        # We don't have a station at destination.
        # I will use the average price of the USA ($3.50?) or the last paid price?
        # Or just not charge it.
        # Let's stick to "Money Spent on Fuel" = Actual Money Spent. 
        # If no stop, $0.
        # But I'll add a note in the response.
        # Wait, if I choose "Return Full", I need a price.
        # I'll just skip it to be literal to "Fuel Ups".
        
        return {
            "stops": stops,
            "total_cost": round(total_fuel_cost, 2)
        }
