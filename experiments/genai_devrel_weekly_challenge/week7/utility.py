from settings import get_settings
import requests
from typing import Dict, Any

settings = get_settings()


def get_weather_tool(location: str) -> Dict[str, Any]:
    """Tool for retrieving weather information for a given location.

    This function combines location geocoding and weather data retrieval
    to provide comprehensive weather information for a named location.

    Args:
        location (str): Name of the location to get weather for

    Returns:
        Dict[str, Any]: A dictionary containing location and weather information
    """
    # First, get the coordinates for the location
    location_data = get_location_coordinates(location)

    if not location_data.get("success", False):
        # If geocoding failed, return the error
        return location_data

    # Then, get the weather data for those coordinates
    weather_data = get_weather_data(
        location_data["latitude"], location_data["longitude"]
    )

    if not weather_data.get("success", False):
        # If weather data retrieval failed, return the error
        return weather_data

    # Combine location and weather data
    return {
        "name": location_data["name"],
        "latitude": location_data["latitude"],
        "longitude": location_data["longitude"],
        "weather": weather_data["weather_description"],
        "temperature": weather_data["temperature"],
        "temperature_unit": weather_data["temperature_unit"],
        "feels_like": weather_data["feels_like"],
    }


def get_location_coordinates(location: str) -> Dict[str, Any]:
    """Convert a location name to geographic coordinates using Google Maps Geocoding API.

    Args:
        location (str): Name of the location to get coordinates for

    Returns:
        Dict[str, Any]: A dictionary containing location information including coordinates
                        or error details if the geocoding fails
    """
    try:
        # Use Google Maps Geocoding API to get lat/lon from location name
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": location, "key": settings.GOOGLE_MAPS_API_KEY}

        response = requests.get(geocode_url, params=params)
        data = response.json()

        if data["status"] == "OK" and data["results"]:
            # Extract latitude and longitude from the first result
            location_data = data["results"][0]
            lat = location_data["geometry"]["location"]["lat"]
            lon = location_data["geometry"]["location"]["lng"]
            formatted_address = location_data["formatted_address"]

            return {
                "name": formatted_address,
                "latitude": lat,
                "longitude": lon,
                "success": True,
            }
        else:
            # If geocoding fails, return an error
            return {
                "error": f"Could not find coordinates for location: {location}",
                "status": data.get("status", "UNKNOWN_ERROR"),
                "success": False,
            }

    except Exception as e:
        # Handle any exceptions that might occur
        return {"error": f"Error getting location data: {str(e)}", "success": False}


def get_weather_data(latitude: float, longitude: float) -> Dict[str, Any]:
    """Get weather information for a specific location using Open-Meteo API.

    Args:
        latitude (float): Latitude of the location
        longitude (float): Longitude of the location

    Returns:
        Dict[str, Any]: A dictionary containing weather information or error details
    """
    try:
        # Use Open-Meteo API to get weather data
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ["temperature_2m", "apparent_temperature", "weather_code"],
            "timezone": "auto",
        }

        response = requests.get(weather_url, params=params)
        data = response.json()

        if "current" in data:
            current = data["current"]
            # Map weather code to a human-readable description
            weather_descriptions = {
                0: "Clear sky",
                1: "Mainly clear",
                2: "Partly cloudy",
                3: "Overcast",
                45: "Fog",
                48: "Depositing rime fog",
                51: "Light drizzle",
                53: "Moderate drizzle",
                55: "Dense drizzle",
                56: "Light freezing drizzle",
                57: "Dense freezing drizzle",
                61: "Slight rain",
                63: "Moderate rain",
                65: "Heavy rain",
                66: "Light freezing rain",
                67: "Heavy freezing rain",
                71: "Slight snow fall",
                73: "Moderate snow fall",
                75: "Heavy snow fall",
                77: "Snow grains",
                80: "Slight rain showers",
                81: "Moderate rain showers",
                82: "Violent rain showers",
                85: "Slight snow showers",
                86: "Heavy snow showers",
                95: "Thunderstorm",
                96: "Thunderstorm with slight hail",
                99: "Thunderstorm with heavy hail",
            }

            weather_code = current.get("weather_code", 0)
            weather_description = weather_descriptions.get(weather_code, "Unknown")

            return {
                "temperature": current.get("temperature_2m"),
                "temperature_unit": data.get("current_units", {}).get(
                    "temperature_2m", "°C"
                ),
                "feels_like": current.get("apparent_temperature"),
                "weather_code": weather_code,
                "weather_description": weather_description,
                "success": True,
            }
        else:
            return {
                "error": "Failed to retrieve weather data",
                "data": data,
                "success": False,
            }

    except Exception as e:
        return {"error": f"Error getting weather data: {str(e)}", "success": False}
