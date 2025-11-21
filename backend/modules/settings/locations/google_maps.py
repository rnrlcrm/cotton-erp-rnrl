"""
Google Maps API Integration

Handles all Google Maps API calls for location data.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import httpx

from backend.modules.settings.locations.schemas import GooglePlaceDetails, GooglePlaceSuggestion


class GoogleMapsService:
    """
    Service for interacting with Google Maps APIs.
    
    APIs used:
    1. Places Autocomplete - for location search suggestions
    2. Place Details - for full location information
    3. Geocoding - backup for reverse lookup
    """
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        if not self.api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set")
        
        self.autocomplete_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        self.details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        self.geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def search_places(self, query: str, country: str = "IN") -> List[GooglePlaceSuggestion]:
        """
        Search for places using Google Places Autocomplete API.
        
        Args:
            query: Search query string
            country: Country code for bias (default: IN for India)
            
        Returns:
            List of place suggestions
        """
        params = {
            "input": query,
            "key": self.api_key,
            "components": f"country:{country}",
            "types": "(regions)"  # Focus on cities, states, regions
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.autocomplete_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("status") != "OK":
                return []
            
            suggestions = []
            for prediction in data.get("predictions", []):
                suggestions.append(GooglePlaceSuggestion(
                    description=prediction.get("description", ""),
                    place_id=prediction.get("place_id", "")
                ))
            
            return suggestions
        
        except Exception as e:
            print(f"Google Maps Autocomplete API error: {e}")
            return []
    
    def fetch_place_details(self, place_id: str) -> Optional[GooglePlaceDetails]:
        """
        Fetch full place details from Google Place Details API.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            GooglePlaceDetails object or None if error
        """
        params = {
            "place_id": place_id,
            "key": self.api_key,
            "fields": "place_id,formatted_address,name,geometry,address_components"
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.details_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("status") != "OK":
                return None
            
            result = data.get("result", {})
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            
            # Parse address components
            components = self._parse_address_components(result.get("address_components", []))
            
            return GooglePlaceDetails(
                place_id=place_id,
                formatted_address=result.get("formatted_address", ""),
                name=result.get("name"),
                latitude=location.get("lat", 0.0),
                longitude=location.get("lng", 0.0),
                address_components=result.get("address_components", {}),
                city=components.get("city"),
                district=components.get("district"),
                state=components.get("state"),
                state_code=components.get("state_code"),
                country=components.get("country"),
                pincode=components.get("pincode")
            )
        
        except Exception as e:
            print(f"Google Maps Place Details API error: {e}")
            return None
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[GooglePlaceDetails]:
        """
        Reverse geocode coordinates to get location details (backup method).
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            GooglePlaceDetails object or None if error
        """
        params = {
            "latlng": f"{latitude},{longitude}",
            "key": self.api_key
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.geocode_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("status") != "OK" or not data.get("results"):
                return None
            
            result = data["results"][0]
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            
            components = self._parse_address_components(result.get("address_components", []))
            
            return GooglePlaceDetails(
                place_id=result.get("place_id", ""),
                formatted_address=result.get("formatted_address", ""),
                name=components.get("city"),
                latitude=location.get("lat", latitude),
                longitude=location.get("lng", longitude),
                address_components=result.get("address_components", {}),
                city=components.get("city"),
                district=components.get("district"),
                state=components.get("state"),
                state_code=components.get("state_code"),
                country=components.get("country"),
                pincode=components.get("pincode")
            )
        
        except Exception as e:
            print(f"Google Maps Geocoding API error: {e}")
            return None
    
    def _parse_address_components(self, components: List[Dict]) -> Dict[str, Optional[str]]:
        """
        Parse Google Maps address components into structured data.
        
        Args:
            components: List of address component dicts from Google
            
        Returns:
            Dict with city, district, state, state_code, country, pincode
        """
        parsed = {
            "city": None,
            "district": None,
            "state": None,
            "state_code": None,
            "country": None,
            "pincode": None
        }
        
        for component in components:
            types = component.get("types", [])
            long_name = component.get("long_name")
            short_name = component.get("short_name")
            
            if "locality" in types:
                parsed["city"] = long_name
            elif "administrative_area_level_3" in types and not parsed["city"]:
                parsed["city"] = long_name
            elif "administrative_area_level_2" in types:
                parsed["district"] = long_name
            elif "administrative_area_level_1" in types:
                parsed["state"] = long_name
                parsed["state_code"] = short_name
            elif "country" in types:
                parsed["country"] = long_name
            elif "postal_code" in types:
                parsed["pincode"] = long_name
        
        return parsed
