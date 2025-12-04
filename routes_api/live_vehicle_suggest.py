"""
Wzbogacanie JSON-a trasy o live dane pojazdu z backendu /data.

Zakładamy, że mamy:
- FastAPI z endpointem /data (zwraca listę wierszy vehicles+trips)
- JSON trasy w formacie jak w response_1764798190916.json, np.:

{
  "route": {
    "distance": "4.9 km",
    "duration": "23 mins",
    "steps": [
      {
        "mode": "WALKING",
        ...
      },
      {
        "mode": "TRANSIT",
        "vehicle_type": "BUS",
        "line": "F1",
        "departure_stop": "Broniewskiego - Kraszewskiego (0052)",
        ...
      }
    ],
    "line_numbers": ["F1"]
  },
  "disabled_lines": [],
  "filtered": false
}

Celem jest dodanie do każdego kroku TRANSIT pola:
step["vehicle_live"] = {...}
"""

import re
from typing import Dict, List, Any, Optional

import requests


# URL do Twojego backendu z /data.
# Jeśli FastAPI z GTFS działa na innym porcie/host, tutaj popraw.
DATA_API_URL = "http://localhost:8000/data"

# Wzorzec wyciągający kod przystanku z końca stringa, np. "(0052)"
STOP_CODE_PATTERN = re.compile(r"\((\d+)\)\s*$")


def extract_stop_code(stop_label: str) -> Optional[str]:
    """
    'Broniewskiego - Kraszewskiego (0052)' -> '0052'
    Jeśli nie ma kodu w nawiasach na końcu, zwraca None.
    """
    if not stop_label:
        return None
    match = STOP_CODE_PATTERN.search(stop_label)
    return match.group(1) if match else None


def classify_delay_status(delay_min: Optional[float]) -> Optional[str]:
    """
    Prosta klasyfikacja opóźnienia w minutach:
    - <= -1   -> "early"
    - -1..1   -> "on_time"
    - > 1     -> "late"
    """
    if delay_min is None:
        return None

    try:
        m = float(delay_min)
    except (TypeError, ValueError):
        return None

    if m <= -1:
        return "early"
    if m <= 1:
        return "on_time"
    return "late"


def find_matching_vehicle(
    vehicles_rows: List[Dict[str, Any]],
    line: str,
    dep_stop_code: str,
) -> Optional[Dict[str, Any]]:
    """
    Szukamy pojazdu w danych z /data:
    - route_id == line (np. "F1")
    - current_stop_id == dep_stop_code (np. "0052")
    Jeśli jest kilka, bierzemy ten z największym timestamp (najświeższy).
    """

    if not line or not dep_stop_code:
        return None

    line_str = str(line)
    stop_str = str(dep_stop_code)

    candidates = [
        v
        for v in vehicles_rows
        if str(v.get("route_id")) == line_str
        and str(v.get("current_stop_id")) == stop_str
    ]

    if not candidates:
        return None

    # sortuj po timestamp (malejąco)
    candidates.sort(key=lambda v: v.get("timestamp") or 0, reverse=True)
    return candidates[0]


def enrich_route_with_live_vehicle_data(route_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Przyjmuje finalny JSON trasy, dodaje do kroków TRANSIT sekcję "vehicle_live"
    z informacjami z backendu /data:

    step["vehicle_live"] = {
        "vehicle_id": ...,
        "route_id": ...,
        "current_stop_id": ...,
        "current_stop_name": ...,
        "arrival_delay_minutes": ...,
        "delay_status": ...,
        "timestamp": ...
    }

    Zwraca zmodyfikowany route_response.
    """

    # bezpieczeństwo: jeśli route/steps nie istnieje, nic nie robimy
    route = route_response.get("route")
    if not route:
        return route_response

    steps = route.get("steps")
    if not isinstance(steps, list):
        return route_response

    # 1. Pobierz live dane z backendu /data
    try:
        resp = requests.get(DATA_API_URL, timeout=5)
        resp.raise_for_status()
        vehicles_rows = resp.json()
        if not isinstance(vehicles_rows, list):
            vehicles_rows = []
    except Exception as e:
        # W razie problemu z backendem /data – nie crashujemy, tylko zwracamy oryginalną trasę
        print(f"[enricher] Błąd podczas pobierania /data: {e}")
        return route_response

    # 2. Dla każdego kroku TRANSIT szukamy pasującego pojazdu
    for step in steps:
        if step.get("mode") != "TRANSIT":
            continue

        line = step.get("line")  # np. "F1"
        dep_stop_label = step.get("departure_stop")  # np. "Broniewskiego... (0052)"
        dep_stop_code = extract_stop_code(dep_stop_label)

        match = find_matching_vehicle(vehicles_rows, line, dep_stop_code)

        if match:
            delay_min = match.get("arrival_delay_minutes")
            delay_status = classify_delay_status(delay_min)

            step["vehicle_live"] = {
                "vehicle_id": match.get("vehicle_id"),
                "route_id": match.get("route_id"),
                "current_stop_id": match.get("current_stop_id"),
                "current_stop_name": match.get("current_stop_name"),
                "arrival_delay_minutes": delay_min,
                "delay_status": delay_status,
                "timestamp": match.get("timestamp"),
            }

    # zaktualizuj steps w strukturze route
    route_response["route"]["steps"] = steps
    return route_response