"""
Funkcje do filtrowania tras na podstawie wyłączonych linii MPK.
"""

from typing import List, Dict, Optional


def extract_line_numbers(route: Dict) -> List[str]:
    """
    Wyciąga numery linii z trasy.

    Args:
        route: Dict z danymi trasy z Google Maps API

    Returns:
        Lista numerów linii (np. ["2", "5", "69A"])
    """
    line_numbers = []

    if "legs" not in route:
        return line_numbers

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

    return line_numbers


def filter_routes_by_disabled_lines(
    routes: List[Dict], disabled_lines: List[str]
) -> List[Dict]:
    """
    Filtruje trasy, usuwając te które używają wyłączonych linii.

    Args:
        routes: Lista tras (Dict) z Google Maps API
        disabled_lines: Lista wyłączonych numerów linii (np. ["2", "5", "69A"])

    Returns:
        Lista tras które NIE używają wyłączonych linii
    """
    if not disabled_lines:
        return routes

    filtered_routes = []

    for route in routes:
        route_lines = extract_line_numbers(route)
        # Sprawdź czy trasa używa jakiejś wyłączonej linii
        uses_disabled = any(line in disabled_lines for line in route_lines)

        if not uses_disabled:
            filtered_routes.append(route)

    return filtered_routes


def find_best_route(routes: List[Dict]) -> Optional[Dict]:
    """
    Znajduje najlepszą trasę (najkrótszą czasowo).

    Args:
        routes: Lista tras (Dict) z Google Maps API

    Returns:
        Najlepsza trasa lub None jeśli brak tras
    """
    if not routes:
        return None

    # Sortuj po czasie podróży (duration value w sekundach)
    sorted_routes = sorted(
        routes,
        key=lambda r: (
            r["legs"][0]["duration"]["value"] if r.get("legs") else float("inf")
        ),
    )

    return sorted_routes[0]
