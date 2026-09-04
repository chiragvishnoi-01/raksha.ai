"""RAKSHA AI - Location & Nearby Hospital Identification (Google Maps / Smart Fallback)"""
import math
import logging
import requests
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger("raksha.location")

DEFAULT_HOSPITALS = [
    {
        "name": "L.L.R. Hospital (Hallet) & Level-1 Trauma Centre",
        "address": "Swaroop Nagar, Kanpur, Uttar Pradesh 208002",
        "latitude": 26.4789,
        "longitude": 80.3218,
        "phone": "+91-512-2535483",
        "type": "Level-1 Trauma & Government Medical College",
        "beds_available": 14,
        "icu_status": "Ready",
    },
    {
        "name": "Regency Hospital Emergency Trauma Wing",
        "address": "A-2, Sarvodaya Nagar, Kanpur, Uttar Pradesh 208005",
        "latitude": 26.4630,
        "longitude": 80.3015,
        "phone": "+91-512-3534000",
        "type": "Super Speciality Critical Care",
        "beds_available": 8,
        "icu_status": "Ready",
    },
    {
        "name": "Fortune Multi-Speciality Hospital",
        "address": "117/Q/40B, Sharda Nagar, Kanpur, Uttar Pradesh 208025",
        "latitude": 26.4862,
        "longitude": 80.2851,
        "phone": "+91-512-2500000",
        "type": "Advanced 24x7 Emergency",
        "beds_available": 5,
        "icu_status": "Ready",
    },
    {
        "name": "Rama Hospital & Research Center",
        "address": "GT Road, Mandhana, Kanpur, Uttar Pradesh 209217",
        "latitude": 26.5412,
        "longitude": 80.2291,
        "phone": "+91-512-2780880",
        "type": "Highway Trauma Center",
        "beds_available": 11,
        "icu_status": "Ready",
    }
]

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def get_google_maps_link(lat: float, lon: float) -> str:
    """Generates direct Google Maps location URL."""
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

def get_directions_link(orig_lat: float, orig_lon: float, dest_lat: float, dest_lon: float) -> str:
    """Generates Google Maps routing directions link."""
    return f"https://www.google.com/maps/dir/?api=1&origin={orig_lat},{orig_lon}&destination={dest_lat},{dest_lon}&travelmode=driving"

def find_nearest_hospitals(latitude: float = None, longitude: float = None) -> List[Dict[str, Any]]:
    """Identifies nearest emergency hospitals using Google Places API if key is set,
    otherwise uses local geographic knowledge base for Kanpur Highway corridor.
    """
    lat = latitude if latitude is not None else settings.LATITUDE
    lon = longitude if longitude is not None else settings.LONGITUDE
    
    # 1. Check if Google Maps API key is configured
    if settings.GOOGLE_MAPS_API_KEY:
        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lon}",
                "radius": 15000,
                "type": "hospital",
                "keyword": "trauma emergency",
                "key": settings.GOOGLE_MAPS_API_KEY
            }
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    hospitals = []
                    for item in results[:4]:
                        h_lat = item["geometry"]["location"]["lat"]
                        h_lon = item["geometry"]["location"]["lng"]
                        dist = haversine_km(lat, lon, h_lat, h_lon)
                        eta_mins = max(4, int(dist * 2.2)) # approx 30km/h emergency speed
                        hospitals.append({
                            "name": item.get("name", "Emergency Hospital"),
                            "address": item.get("vicinity", "Nearby Emergency Center"),
                            "latitude": h_lat,
                            "longitude": h_lon,
                            "distance_km": dist,
                            "eta_minutes": eta_mins,
                            "phone": "+91-102 (National Ambulance)",
                            "type": "Identified via Google Places API",
                            "maps_url": get_directions_link(lat, lon, h_lat, h_lon)
                        })
                    logger.info(f"Retrieved {len(hospitals)} hospitals from Google Places API.")
                    return sorted(hospitals, key=lambda x: x["distance_km"])
        except Exception as e:
            logger.warning(f"Google Places API request failed: {e}. Falling back to default hospital directory.")

    # 2. Fallback using curated Kanpur / NH-27 emergency hospitals
    results = []
    for h in DEFAULT_HOSPITALS:
        dist = haversine_km(lat, lon, h["latitude"], h["longitude"])
        eta_mins = max(3, int(dist * 2.2))
        item = dict(h)
        item["distance_km"] = dist
        item["eta_minutes"] = eta_mins
        item["maps_url"] = get_directions_link(lat, lon, h["latitude"], h["longitude"])
        results.append(item)
    
    # Sort by closest distance
    results.sort(key=lambda x: x["distance_km"])
    return results

def get_primary_hospital(latitude: float = None, longitude: float = None) -> Dict[str, Any]:
    """Returns the primary (nearest) emergency hospital."""
    hospitals = find_nearest_hospitals(latitude, longitude)
    return hospitals[0] if hospitals else {
        "name": "General Emergency Trauma Unit",
        "address": "District Emergency Center",
        "distance_km": 4.5,
        "eta_minutes": 10,
        "phone": "108 / 112",
        "maps_url": get_google_maps_link(settings.LATITUDE, settings.LONGITUDE)
    }
