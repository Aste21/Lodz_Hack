import re
from typing import Dict, List, Any, Optional

import requests

# URL do Twojego backendu z /data
DATA_API_URL = "http://localhost:8001/data"

# Szukamy kodu przystanku w nawiasach na końcu, np. "Broniewskiego (0052)"
STOP_CODE_PATTERN = re.compile(r"\((\d+)\)\s*$")


def extract_stop_code(stop_label: str) -> Optional[str]:
    """
    'Broniewskiego - Kraszewskiego (0052)' -> '0052'
    Jeśli nie ma kodu, zwraca None.
    """
    if not stop_label:
        return None
    m = STOP_CODE_PATTERN.search(stop_label)
    return m.group(1) if m else None


def classify_delay_status(delay_min: Optional[float]) -> Optional[str]:
    """
    Prosta klasyfikacja opóźnienia:
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
    dep_stop_code: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Szukamy pojazdu dla danej linii (line) i ew. przystanku początkowego.

    Strategia:
    1) Filtrowanie po route_id == line
    2) Jeśli mamy dep_stop_code:
         - próbujemy zawęzić po current_stop_id == dep_stop_code
    3) Jeśli nadal brak kandydatów → bierzemy dowolny pojazd z tej linii
       (najświeższy po timestamp).

    Zwraca jeden dict (wiersz), albo None.
    """
    if not line:
        return None

    line_str = str(line)

    # 1. wszystkie pojazdy danej linii
    base_candidates = [v for v in vehicles_rows if str(v.get("route_id")) == line_str]

    if not base_candidates:
        return None

    # 2. jeżeli mamy kod przystanku, próbujemy dopasować po current_stop_id
    if dep_stop_code:
        stop_str = str(dep_stop_code)
        strong_candidates = [
            v for v in base_candidates if str(v.get("current_stop_id")) == stop_str
        ]
        if strong_candidates:
            base_candidates = strong_candidates

    # 3. wybieramy najświeższy po timestamp
    base_candidates.sort(key=lambda v: v.get("timestamp") or 0, reverse=True)
    return base_candidates[0]


def enrich_route_with_live_vehicle_data(
    route_response: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Dodaje do kroków TRANSIT pole "vehicle_live" z informacjami z backendu /data:

    step["vehicle_live"] = {
        "vehicle_id": ...,
        "route_id": ...,
        "current_stop_id": ...,
        "current_stop_name": ...,
        "arrival_delay_minutes": ...,
        "delay_status": ...,
        "timestamp": ...
    }
    """
    route = route_response.get("route")
    if not route:
        return route_response

    steps = route.get("steps")
    if not isinstance(steps, list):
        return route_response

    # 1. Pobierz dane z /data
    try:
        resp = requests.get(DATA_API_URL, timeout=5)
        resp.raise_for_status()
        vehicles_rows = resp.json()
        if not isinstance(vehicles_rows, list):
            vehicles_rows = []
    except Exception as e:
        print(f"[enricher] Błąd pobierania /data: {e}")
        return route_response

    # 2. Dla każdego kroku TRANSIT spróbuj znaleźć pojazd
    for step in steps:
        if step.get("mode") != "TRANSIT":
            continue

        line = step.get("line")  # np. "F1", "76"
        dep_stop_label = step.get("departure_stop")
        dep_stop_code = extract_stop_code(dep_stop_label)  # może być None

        match = find_matching_vehicle(vehicles_rows, line, dep_stop_code)

        print(f"match: ==={match}===")

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
        else:
            # brak dopasowania – jawnie wpisujemy None, żeby frontend wiedział, co się stało
            print(
                f"[enricher] Brak pojazdu dla linii {line} i przystanku {dep_stop_code}"
            )
            step["vehicle_live"] = None

    route_response["route"]["steps"] = steps
    return route_response
