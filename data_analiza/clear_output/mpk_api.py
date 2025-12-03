import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google.transit import gtfs_realtime_pb2
import requests
import pandas as pd
from fastapi_utils.tasks import repeat_every
from pipeline.pipeline import (
    build_datasets_from_feeds,
    fetch_feed,
)

app = FastAPI(title="Lodz GTFS-RT API + Pipeline")


VEHICLE_POSITIONS_URL = "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/vehicle_positions.bin"
TRIP_UPDATES_URL = "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/trip_updates.bin"


def fetch_gtfs_feed(url: str) -> gtfs_realtime_pb2.FeedMessage:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(resp.content)
    return feed


@app.post("/refresh")
def refresh_data():
    """
    Ręczne odświeżenie danych:
    - pobiera 2 feedy GTFS-RT
    - odpala pipeline
    """
    try:
        vehicle_feed = fetch_gtfs_feed(VEHICLE_POSITIONS_URL)
        trip_feed = fetch_gtfs_feed(TRIP_UPDATES_URL)

        vehicles_df, trips_df = build_datasets_from_feeds(vehicle_feed, trip_feed)

        return {
            "status": "ok",
            "vehicles_rows": len(vehicles_df),
            "trips_rows": len(trips_df),
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching GTFS-RT: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")


@app.get("/data")
def get_all_data():
    """
    Pobiera live GTFS-RT z Łodzi, przepuszcza przez pipeline
    i zwraca:
    {
      "vehicles": [...],
      "trips": [...]
    }
    """
    try:
        vehicle_feed = fetch_feed(VEHICLE_POSITIONS_URL)
        trip_feed    = fetch_feed(TRIP_UPDATES_URL)

        vehicles_df, trips_df = build_datasets_from_feeds(vehicle_feed, trip_feed)

        return {
            "vehicles": vehicles_df.to_dict(orient="records"),
            "trips": trips_df.to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")