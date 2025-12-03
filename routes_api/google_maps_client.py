"""
Klient do Google Maps Directions API dla tras komunikacją miejską.
"""

import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    raise RuntimeError("Brak GOOGLE_MAPS_API_KEY w .env")


def get_single_route(origin: str, destination: str) -> Optional[Dict]:
    """
    Pobiera jedną trasę komunikacją miejską z punktu A do B.

    Args:
        origin: Punkt startowy (adres lub współrzędne)
        destination: Punkt docelowy (adres lub współrzędne)

    Returns:
        Dict z danymi trasy lub None jeśli błąd
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"

    params = {
        "origin": origin,
        "destination": destination,
        "mode": "transit",
        "key": API_KEY,
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if data.get("status") != "OK":
            error_msg = data.get("error_message", "Directions failed")
            print(f"Błąd Google Maps API: {error_msg}")
            return None

        if not data.get("routes"):
            return None

        route = data["routes"][0]
        return route
    except Exception as e:
        print(f"Błąd podczas pobierania trasy: {e}")
        return None


def get_all_routes(origin: str, destination: str) -> List[Dict]:
    """
    Pobiera wszystkie dostępne trasy komunikacją miejską z punktu A do B.

    Args:
        origin: Punkt startowy (adres lub współrzędne)
        destination: Punkt docelowy (adres lub współrzędne)

    Returns:
        Lista tras (Dict) lub pusta lista jeśli błąd
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"

    params = {
        "origin": origin,
        "destination": destination,
        "mode": "transit",
        "alternatives": "true",  # Prosimy o alternatywne trasy
        "key": API_KEY,
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if data.get("status") != "OK":
            error_msg = data.get("error_message", "Directions failed")
            print(f"Błąd Google Maps API: {error_msg}")
            return []

        routes = data.get("routes", [])
        return routes
    except Exception as e:
        print(f"Błąd podczas pobierania tras: {e}")
        return []


def format_route_response(route: Dict) -> Dict:
    """
    Formatuje trasę do odpowiedzi API.

    Args:
        route: Dict z danymi trasy z Google Maps API

    Returns:
        Sformatowany Dict z trasą
    """
    if not route or "legs" not in route:
        return {}

    leg = route["legs"][0]

    # Współrzędne startu i końca całej trasy
    start_location = leg["start_location"]
    end_location = leg["end_location"]

    steps = []
    for step in leg["steps"]:
        travel_mode = step["travel_mode"]
        step_data = {
            "mode": travel_mode,
            "distance": step["distance"]["text"],
            "duration": step["duration"]["text"],
            "start_location": {
                "lat": step["start_location"]["lat"],
                "lng": step["start_location"]["lng"],
            },
            "end_location": {
                "lat": step["end_location"]["lat"],
                "lng": step["end_location"]["lng"],
            },
        }

        # Dodaj polyline jeśli jest dostępny (dla rysowania na mapie)
        if "polyline" in step:
            step_data["polyline"] = step["polyline"]["points"]

        if travel_mode == "WALKING":
            step_data["instruction"] = f"PIESZO – {step['distance']['text']}"
        elif travel_mode == "TRANSIT":
            t = step["transit_details"]
            line = t["line"]
            vehicle_type = line["vehicle"]["type"]  # BUS / TRAM / SUBWAY / TRAIN / RAIL
            line_name = line.get("short_name") or line.get("name")
            num_stops = t["num_stops"]
            dep_stop = t["departure_stop"]["name"]
            arr_stop = t["arrival_stop"]["name"]

            # Współrzędne przystanków
            dep_stop_location = t["departure_stop"].get("location", {})
            arr_stop_location = t["arrival_stop"].get("location", {})

            step_data.update(
                {
                    "vehicle_type": vehicle_type,
                    "line": line_name,
                    "departure_stop": dep_stop,
                    "arrival_stop": arr_stop,
                    "num_stops": num_stops,
                    "instruction": f"{vehicle_type}: linia {line_name}, z {dep_stop} do {arr_stop} ({num_stops} przystanków)",
                    "departure_stop_location": (
                        {
                            "lat": dep_stop_location.get("lat"),
                            "lng": dep_stop_location.get("lng"),
                        }
                        if dep_stop_location
                        else None
                    ),
                    "arrival_stop_location": (
                        {
                            "lat": arr_stop_location.get("lat"),
                            "lng": arr_stop_location.get("lng"),
                        }
                        if arr_stop_location
                        else None
                    ),
                }
            )

        steps.append(step_data)

    # Wyciągnij numery linii
    line_numbers = []
    for leg in route["legs"]:
        if "steps" not in leg:
            continue
        for step in leg["steps"]:
            if step.get("travel_mode") == "TRANSIT":
                transit_details = step.get("transit_details", {})
                line = transit_details.get("line", {})
                line_name = line.get("short_name") or line.get("name")
                if line_name:
                    line_numbers.append(str(line_name))

    # Overview polyline dla całej trasy (jeśli dostępny)
    overview_polyline = None
    if "overview_polyline" in route:
        overview_polyline = route["overview_polyline"]["points"]

    return {
        "distance": leg["distance"]["text"],
        "duration": leg["duration"]["text"],
        "start_location": {
            "lat": start_location["lat"],
            "lng": start_location["lng"],
        },
        "end_location": {
            "lat": end_location["lat"],
            "lng": end_location["lng"],
        },
        "overview_polyline": overview_polyline,  # Polyline dla całej trasy (do rysowania na mapie)
        "steps": steps,
        "line_numbers": line_numbers,
    }
