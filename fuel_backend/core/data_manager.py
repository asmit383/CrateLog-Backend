import pandas as pd
import os
from django.conf import settings
from scipy.spatial import cKDTree

class FuelStationManager:
    _instance = None
    df = None
    tree = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = FuelStationManager()
            cls._instance.load_data()
        return cls._instance

    def load_data(self):
        print("Loading Fuel and City Data...")
        base_dir = settings.BASE_DIR
        
        # Load Data
        fuel_path = os.path.join(base_dir, 'fuel-prices-for-be-assessment.csv')
        cities_path = os.path.join(base_dir, 'us_cities.csv')
        
        fuel_df = pd.read_csv(fuel_path)
        cities_df = pd.read_csv(cities_path)
        
        # Normalize for Merge
        # We need coordinates for the fuel stations.
        # We merge based on City + State.
        fuel_df['City_Norm'] = fuel_df['City'].astype(str).str.strip().str.upper()
        fuel_df['State_Norm'] = fuel_df['State'].astype(str).str.strip().str.upper()
        
        cities_df['City_Norm'] = cities_df['CITY'].astype(str).str.strip().str.upper()
        cities_df['State_Norm'] = cities_df['STATE_CODE'].astype(str).str.strip().str.upper()
        
        # Deduplicate cities (take first match)
        cities_lookup = cities_df.drop_duplicates(subset=['City_Norm', 'State_Norm'])
        
        # Merge to get Lat/Lon for Fuel Stations
        self.df = pd.merge(fuel_df, cities_lookup[['City_Norm', 'State_Norm', 'LATITUDE', 'LONGITUDE']], 
                           on=['City_Norm', 'State_Norm'], how='inner')
        
        # Rename for clarity
        self.df.rename(columns={'LATITUDE': 'lat', 'LONGITUDE': 'lon', 'Retail Price': 'price', 'Truckstop Name': 'name', 'Address': 'address'}, inplace=True)
        
        # Drop invalid rows
        self.df.dropna(subset=['lat', 'lon', 'price'], inplace=True)
        
        print(f"Loaded {len(self.df)} fuel stations with coordinates.")
        
        # Build Spatial Tree for fast querying
        # KDTree expects (x, y) -> (lon, lat) usually, or we can just use 2D points.
        # For small distances, Equirectangular approximation is okay for nearest neighbour search, 
        # but for accuracy we should project. However, for "finding stations near route", 
        # a simple lat/lon KDTree is fast and 'good enough' for this assignment scale.
        self.points = self.df[['lat', 'lon']].values
        self.tree = cKDTree(self.points)

    def find_nearby_stations(self, lat, lon, radius_deg=0.5):
        # radius_deg: 1 deg approx 69 miles. 0.1 deg approx 7 miles.
        # We want stations within ~10 miles of the point.
        # 10 miles ~ 0.15 degrees.
        indices = self.tree.query_ball_point([lat, lon], r=radius_deg)
        return self.df.iloc[indices]

class CityGeocoder:
    _instance = None
    df = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CityGeocoder()
            cls._instance.load_data()
        return cls._instance

    def load_data(self):
        base_dir = settings.BASE_DIR
        cities_path = os.path.join(base_dir, 'us_cities.csv')
        self.df = pd.read_csv(cities_path)
        # Create multiple lookup keys:
        # 1. "city, state_code" (e.g. "phoenix, az")
        # 2. "city, state_name" (e.g. "phoenix, arizona")
        
        self.df['key_code'] = self.df['CITY'].str.lower().str.strip() + ", " + self.df['STATE_CODE'].str.lower().str.strip()
        self.df['key_name'] = self.df['CITY'].str.lower().str.strip() + ", " + self.df['STATE_NAME'].str.lower().str.strip()

    def geocode(self, query):
        # Query format: "City, StateCode" or "City, StateName"
        query = query.lower().strip()
        
        # Try match with code
        match = self.df[self.df['key_code'] == query]
        if match.empty:
            # Try match with full name
            match = self.df[self.df['key_name'] == query]
            
        if not match.empty:
            row = match.iloc[0]
            return row['LATITUDE'], row['LONGITUDE']
        
        return None
