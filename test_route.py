import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    raise RuntimeError("Brak GOOGLE_MAPS_API_KEY w .env")

def compute_route(origin: str, destination: str):
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
    }

    body = {
        "origin": {
            "address": origin
        },
        "destination": {
            "address": destination
        },
        "travelMode": "DRIVE",
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))

    print("Status code:", response.status_code)
    print("Raw response:", response.text)

    if response.status_code != 200:
        raise RuntimeError("Request failed")

    data = response.json()
    route = data["routes"][0]

    distance_m = route["distanceMeters"]
    duration = route["duration"]
    polyline = route["polyline"]["encodedPolyline"]

    print("\n✅ Udało się policzyć trasę!")
    print("Dystans (m):", distance_m)
    print("Czas (ISO duration):", duration)
    print("Polyline (encoded):", polyline[:60] + "...")


if __name__ == "__main__":
    compute_route("Łódź, Poland", "Warsaw, Poland")