from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .data_manager import FuelStationManager, CityGeocoder
from .routing import RouteService
from .optimizer import RouteOptimizer
import logging

logger = logging.getLogger(__name__)

class RouteView(APIView):
    def post(self, request):
        """
        Input: 
        {
            "start": "City, State",
            "finish": "City, State"
        }
        """
        data = request.data
        start_query = data.get('start')
        finish_query = data.get('finish')
        
        if not start_query or not finish_query:
            return Response({"error": "Missing start or finish location."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 1. Geocode
        print(f"Geocoding {start_query} and {finish_query}...")
        geocoder = CityGeocoder.get_instance()
        start_coords = geocoder.geocode(start_query)
        finish_coords = geocoder.geocode(finish_query)
        print(f"Coords: {start_coords}, {finish_coords}")
        
        if not start_coords:
            return Response({"error": f"Could not find start location: {start_query}"}, status=status.HTTP_400_BAD_REQUEST)
        if not finish_coords:
            return Response({"error": f"Could not find finish location: {finish_query}"}, status=status.HTTP_400_BAD_REQUEST)
            
        # 2. Route
        print("Fetching route from OSRM...")
        
        router = RouteService()
        try:
            route_data = router.get_route(start_coords, finish_coords)
            print(f"Route fetched. Distance: {route_data['distance_miles']} miles. Points: {len(route_data['path'])}")
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        # 3. Optimize
        print("Optimizing route...")
        optimizer = RouteOptimizer(route_data)
        try:
            result = optimizer.optimize()
            print("Optimization complete.")
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return Response({"error": f"Optimization Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        # 4. Construct Response
        return_map = data.get('return_map', True)
        
        response_data = {
            "route": {
                "start": start_query,
                "finish": finish_query,
                "distance_miles": round(route_data['distance_miles'], 2),
            },
            "fuel_stops": result.get('stops', []),
            "total_fuel_cost": result.get('total_cost', 0)
        }
        
        if return_map:
            response_data["route"]["map_geometry"] = route_data['geojson']
        
        return Response(response_data)
