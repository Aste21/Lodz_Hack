"""
Klient do Google Maps Directions API dla tras komunikacją miejską.
"""

import os
from typing import List, Dict, Optional

import requests
from dotenv import load_dotenv

from live_vehicle_suggest import enrich_route_with_live_vehicle_data

# === Konfiguracja ===

load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    raise RuntimeError("Brak GOOGLE_MAPS_API_KEY w .env")

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"


# === Funkcje pomocnicze ===

def _build_directions_params(
    origin: str,
    destination: str,
    departure_time: Optional[str] = "now",
) -> Dict[str, str]:
    """
    Buduje parametry do zapytania Directions API (tryb TRANSIT domyślnie).
    """
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "transit",
        "key": API_KEY,
        "language": "pl",
    }

    if departure_time is not None:
        # "now" albo timestamp w sekundach
        params["departure_time"] = departure_time

    return params


def call_directions_api(
    origin: str,
    destination: str,
    departure_time: Optional[str] = "now",
) -> Dict:
    """
    Wywołuje Google Directions API i zwraca surowy JSON.
    """
    params = _build_directions_params(origin, destination, departure_time)
    resp = requests.get(DIRECTIONS_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    status = data.get("status")
    if status != "OK":
        raise RuntimeError(f"Directions API error: {status}, details: {data.get('error_message')}")

    return data


# === Formatowanie trasy do naszego formatu ===

def format_route_response(route: Dict) -> Dict:
    """
    Formatuje pojedynczą trasę z Directions API do odpowiedzi API naszej aplikacji.

    Args:
        route: Dict z danymi trasy z Google Maps API (pojedyncza 'route' z listy 'routes')

    Returns:
        Sformatowany Dict w strukturze:
        {
          "route": {
            "distance": ...,
            "duration": ...,
            "start_location": {...},
            "end_location": {...},
            "overview_polyline": "...",
            "steps": [...],
            "line_numbers": [...]
          },
          "disabled_lines": [],
          "filtered": False
        }
        + wzbogacony o "vehicle_live" w krokach TRANSIT
    """
    if not route or "legs" not in route:
        return {}

    leg = route["legs"][0]

    # Współrzędne startu i końca całej trasy
    start_location = leg["start_location"]
    end_location = leg["end_location"]

    steps: List[Dict] = []

    for step in leg["steps"]:
        travel_mode = step["travel_mode"]
        step_data: Dict = {
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

        # Polyline dla tego kroku (np. do rysowania segmentu trasy)
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
                    "instruction": (
                        f"{vehicle_type}: linia {line_name}, z {dep_stop} "
                        f"do {arr_stop} ({num_stops} przystanków)"
                    ),
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

    # --- Podsumowanie trasy (cały leg) ---

    distance = leg["distance"]["text"]
    duration = leg["duration"]["text"]

    # Całościowy polyline trasy (overview)
    overview_polyline = None
    if "overview_polyline" in route:
        overview_polyline = route["overview_polyline"].get("points")

    # Linie komunikacji zbiorowej użyte w trasie
    line_numbers = sorted(
        {
            s["line"]
            for s in steps
            if s.get("mode") == "TRANSIT" and s.get("line")
        }
    )

    # Bazowy obiekt odpowiedzi
    route_response: Dict = {
        "route": {
            "distance": distance,
            "duration": duration,
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
        },
        "disabled_lines": [],
        "filtered": False,
    }

    # 🔥 Wzbogacenie o live dane pojazdów z backendu /data
    route_response = enrich_route_with_live_vehicle_data(route_response)

    return route_response


# === Główna funkcja eksportowana na zewnątrz ===

def get_transit_route(
    origin: str,
    destination: str,
    departure_time: Optional[str] = "now",
) -> Dict:
    """
    High-level:
    - wywołuje Google Directions API (mode=transit),
    - bierze pierwszą trasę,
    - formatuje ją do naszego formatu,
    - wzbogaca o live dane z MPK.

    Zwraca: gotowy JSON do wysłania przez API frontowi.
    """
    data = call_directions_api(origin, destination, departure_time)
    routes = data.get("routes") or []
    if not routes:
        raise RuntimeError("Brak tras w odpowiedzi Directions API")

    route = routes[0]  # na razie bierzemy pierwszą trasę
    return format_route_response(route)