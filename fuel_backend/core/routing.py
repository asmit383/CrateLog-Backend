import requests
import polyline

class RouteService:
    BASE_URL = "http://router.project-osrm.org/route/v1/driving"

    def get_route(self, start_coords, end_coords):
        """
        start_coords: (lat, lon)
        end_coords: (lat, lon)
        """
        # OSRM expects: lon,lat;lon,lat
        loc_str = f"{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
        url = f"{self.BASE_URL}/{loc_str}?overview=full&geometries=geojson"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] != 'Ok':
                raise Exception(f"OSRM Error: {data['code']}")
            
            route = data['routes'][0]
            distance_meters = route['distance']
            distance_miles = distance_meters * 0.000621371
            
            geometry = route['geometry'] # GeoJSON {type: LineString, coordinates: [[lon, lat], ...]}
            coordinates = geometry['coordinates'] # List of [lon, lat]
            
            # Convert [lon, lat] to [lat, lon] for internal use if needed, 
            # but standard GeoJSON is lon, lat. 
            # Let's keep consistent: internal logic usually lat, lon.
            path_points = [(p[1], p[0]) for p in coordinates]
            
            return {
                'distance_miles': distance_miles,
                'path': path_points, # list of (lat, lon)
                'geojson': geometry
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Routing API Error: {str(e)}")
