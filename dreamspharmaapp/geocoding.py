"""
Geocoding utility for reverse geocoding (coordinates to address)
Supports multiple providers: Google Maps, OpenStreetMap (Nominatim)
"""

import requests
import logging
from django.conf import settings
from decimal import Decimal

logger = logging.getLogger(__name__)


class GeocodingException(Exception):
    """Custom exception for geocoding errors"""
    pass


class GeocodeProvider:
    """Base class for geocoding providers"""
    
    @staticmethod
    def reverse_geocode(latitude, longitude):
        """Reverse geocode coordinates to address"""
        raise NotImplementedError


class GoogleMapsGeocoder(GeocodeProvider):
    """Google Maps Geocoding API provider"""
    
    API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        if not self.api_key:
            raise GeocodingException("Google Maps API key not configured")
    
    def reverse_geocode(self, latitude, longitude):
        """
        Reverse geocode using Google Maps API
        
        Args:
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate
        
        Returns:
            dict: Address components {
                'full_address': str,
                'street': str,
                'city': str,
                'state': str,
                'country': str,
                'pincode': str,
                'locality': str,
                'accuracy': str
            }
        """
        try:
            params = {
                'latlng': f"{latitude},{longitude}",
                'key': self.api_key,
                'language': 'en'
            }
            
            response = requests.get(self.API_URL, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'ZERO_RESULTS':
                raise GeocodingException("No address found for these coordinates")
            
            if data['status'] != 'OK':
                logger.error(f"Google Maps API error: {data['status']}")
                raise GeocodingException(f"Geocoding failed: {data['status']}")
            
            results = data.get('results', [])
            if not results:
                raise GeocodingException("No results returned from Google Maps")
            
            # Parse first result (most accurate)
            first_result = results[0]
            address_components = first_result.get('address_components', [])
            
            address_dict = {}
            for component in address_components:
                component_type = component['types'][0]
                address_dict[component_type] = component['long_name']
            
            # Extract components
            street = address_dict.get('route', '')
            street_number = address_dict.get('street_number', '')
            full_street = f"{street_number} {street}".strip()
            
            city = address_dict.get('locality', '')
            state = address_dict.get('administrative_area_level_1', '')
            country = address_dict.get('country', '')
            pincode = address_dict.get('postal_code', '')
            locality = address_dict.get('sublocality_level_1', address_dict.get('locality', ''))
            
            return {
                'full_address': first_result.get('formatted_address', ''),
                'street': full_street,
                'city': city,
                'state': state,
                'country': country,
                'pincode': pincode,
                'locality': locality,
                'accuracy': first_result.get('geometry', {}).get('location_type', 'ROOFTOP'),
                'latitude': latitude,
                'longitude': longitude
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Maps API request failed: {str(e)}")
            raise GeocodingException(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Google Maps geocoding error: {str(e)}")
            raise GeocodingException(f"Geocoding error: {str(e)}")


class NominatimGeocoder(GeocodeProvider):
    """OpenStreetMap Nominatim Geocoding (Free, no API key required)"""
    
    API_URL = "https://nominatim.openstreetmap.org/reverse"
    USER_AGENT = "DreamPharma/1.0"
    
    def reverse_geocode(self, latitude, longitude):
        """
        Reverse geocode using OpenStreetMap Nominatim API
        
        Args:
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate
        
        Returns:
            dict: Address components
        """
        try:
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'zoom': 18,
                'addressdetails': 1,
                'accept-language': 'en'
            }
            
            headers = {'User-Agent': self.USER_AGENT}
            
            response = requests.get(self.API_URL, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                raise GeocodingException(f"Nominatim error: {data.get('error', 'Unknown error')}")
            
            address = data.get('address', {})
            
            # Extract components from Nominatim response
            street = address.get('road', address.get('street', ''))
            city = address.get('city', address.get('town', address.get('village', '')))
            state = address.get('state', '')
            country = address.get('country', '')
            pincode = address.get('postcode', '')
            locality = address.get('suburb', address.get('city_district', city))
            
            # Full address from display_name
            full_address = data.get('display_name', '')
            
            # Determine accuracy based on result type
            accuracy = data.get('type', 'ROOFTOP')
            if data.get('type') == 'administrative':
                accuracy = 'APPROXIMATE'
            elif data.get('type') in ['building', 'house', 'office']:
                accuracy = 'ROOFTOP'
            else:
                accuracy = 'GEOMETRIC_CENTER'
            
            return {
                'full_address': full_address,
                'street': street,
                'city': city,
                'state': state,
                'country': country,
                'pincode': pincode,
                'locality': locality,
                'accuracy': accuracy,
                'latitude': latitude,
                'longitude': longitude
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Nominatim API request failed: {str(e)}")
            raise GeocodingException(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Nominatim geocoding error: {str(e)}")
            raise GeocodingException(f"Geocoding error: {str(e)}")


def get_geocoder():
    """
    Factory function to get appropriate geocoder instance
    Prefers Google Maps if API key configured, falls back to Nominatim
    """
    try:
        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        if api_key:
            return GoogleMapsGeocoder(api_key)
    except Exception as e:
        logger.warning(f"Google Maps not available: {str(e)}, falling back to Nominatim")
    
    # Default to free Nominatim
    return NominatimGeocoder()


def reverse_geocode(latitude, longitude):
    """
    Reverse geocode coordinates to human-readable address
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
    
    Returns:
        dict: Address components
    
    Raises:
        GeocodingException: If geocoding fails
    """
    geocoder = get_geocoder()
    return geocoder.reverse_geocode(latitude, longitude)


def validate_coordinates(latitude, longitude):
    """
    Validate latitude and longitude values
    
    Args:
        latitude (float): Latitude (-90 to 90)
        longitude (float): Longitude (-180 to 180)
    
    Returns:
        bool: True if valid
    
    Raises:
        GeocodingException: If coordinates are invalid
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
        
        if lat < -90 or lat > 90:
            raise GeocodingException(f"Invalid latitude: {latitude}. Must be between -90 and 90")
        
        if lon < -180 or lon > 180:
            raise GeocodingException(f"Invalid longitude: {longitude}. Must be between -180 and 180")
        
        return True
        
    except ValueError:
        raise GeocodingException(f"Coordinates must be numeric values")


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates (Haversine formula)
    
    Args:
        lat1, lon1: First coordinate pair
        lat2, lon2: Second coordinate pair
    
    Returns:
        float: Distance in kilometers
    """
    from math import radians, cos, sin, asin, sqrt
    
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    
    return c * r
