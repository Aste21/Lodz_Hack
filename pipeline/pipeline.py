from pathlib import Path
import math
import pandas as pd
import requests
from google.transit import gtfs_realtime_pb2

# === ŚCIEŻKI ===

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ⇩ jeśli stops.txt leży gdzie indziej, tu popraw
STOPS_PATH = PROJECT_ROOT / "pipeline" / "stops.txt"

# === LISTY LINII ===

TRAM_ROUTES = {
    "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "10A", "10B",
    "11", "12", "14", "15",
    "16", "17", "18", "19",
    "41", "43", "45",
}

BUS_ROUTES = {
    "Z", "Z3", "Z13",
    "50A", "50B",
    "51A", "51B",
    "52",
    "53A", "53B",
    "54A", "54B",
    "55A", "55B",
    "56",
    "57",
    "58A", "58B",
    "59",
    "60A", "60B", "60C", "60D",
    "61", "62", "63",
    "64A", "64B",
    "65A", "65B",
    "66",
    "68",
    "69A", "69B",
    "70",
    "71A", "71B",
    "72A", "72B",
    "73",
    "75A", "75B",
    "76",
    "77",
    "78",
    "80A", "80B",
    "81A", "81B",
    "82A", "82B",
    "83",
    "84A", "84B",
    "85A", "85B",
    "86",
    "87A", "87B",
    "88A", "88B", "88C", "88D",
    "89", "90",
    "91A", "91B", "91C",
    "92A", "92B",
    "93",
    "94",
    "96",
    "97A", "97B",
    "99",
    "201", "202",
    "F1", "G1", "G2", "H", "W",
}

NOCNE_BUS_ROUTES = {
    "N1A", "N1B",
    "N2",
    "N3A", "N3B",
    "N4A", "N4B",
    "N5A", "N5B",
    "N6",
    "N7A", "N7B",
    "N8",
    "N9",
}


def classify_route_type(route_id: str) -> str:
    """
    Zwraca: 'tramwaj', 'autobus', 'nocny_autobus' albo 'unknown'
    na podstawie route_id.
    """
    if pd.isna(route_id):
        return "unknown"
    r = str(route_id).strip()

    if r in TRAM_ROUTES:
        return "tramwaj"
    if r in BUS_ROUTES:
        return "autobus"
    if r in NOCNE_BUS_ROUTES:
        return "nocny_autobus"
    return "unknown"


# === POBIERANIE GTFS-RT ===

def fetch_feed(url: str) -> gtfs_realtime_pb2.FeedMessage:
    """
    Pobiera GTFS-RT bin i parsuje do FeedMessage().
    Używane w mpk_api.py.
    """
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    return feed


# === PARSOWANIE FEEDÓW DO DATAFRAME ===

def parse_vehicle_positions_feed(feed: gtfs_realtime_pb2.FeedMessage) -> pd.DataFrame:
    """
    Zamienia VehiclePositions GTFS-RT na DataFrame.
    Każdy vehicle -> jeden wiersz.
    """
    rows = []
    entity_counter = 0
    for entity in feed.entity:
        if entity.HasField("vehicle"):
            entity_counter += 1
            v = entity.vehicle
            rows.append({
                "entity_id": entity_counter,
                "vehicle_id": v.vehicle.id if v.vehicle.HasField("id") else None,
                "trip_id": v.trip.trip_id if v.trip.HasField("trip_id") else None,
                "route_id": v.trip.route_id if v.trip.HasField("route_id") else None,
                "latitude": v.position.latitude if v.position.HasField("latitude") else None,
                "longitude": v.position.longitude if v.position.HasField("longitude") else None,
                "current_stop_id": v.stop_id if v.HasField("stop_id") else None,
                "current_stop_sequence": (
                    v.current_stop_sequence if v.HasField("current_stop_sequence") else None
                ),
                "current_status": (
                    int(v.current_status) if v.HasField("current_status") else None
                ),
                "timestamp": v.timestamp if v.HasField("timestamp") else None,
            })
    return pd.DataFrame(rows)


def parse_trip_updates_feed(feed: gtfs_realtime_pb2.FeedMessage) -> pd.DataFrame:
    """
    Zamienia TripUpdates GTFS-RT na DataFrame.
    Każdy StopTimeUpdate -> osobny wiersz.
    """
    rows = []
    entity_counter = 0
    for entity in feed.entity:
        if entity.HasField("trip_update"):
            entity_counter += 1
            tu = entity.trip_update

            base = {
                "entity_id": entity_counter,
                "tu_trip_id": tu.trip.trip_id if tu.trip.HasField("trip_id") else None,
                "tu_route_id": tu.trip.route_id if tu.trip.HasField("route_id") else None,
                "tu_direction_id": tu.trip.direction_id if tu.trip.HasField("direction_id") else None,
                "tu_start_time": tu.trip.start_time if tu.trip.HasField("start_time") else None,
            }

            for stu in tu.stop_time_update:
                # schedule_relationship jako int (enum)
                if stu.HasField("schedule_relationship"):
                    sched_rel = int(stu.schedule_relationship)
                else:
                    sched_rel = None

                # arrival_delay
                if stu.HasField("arrival") and stu.arrival.HasField("delay"):
                    delay = stu.arrival.delay
                else:
                    delay = None

                rows.append({
                    **base,
                    "stop_id": stu.stop_id if stu.HasField("stop_id") else None,
                    "stop_sequence": stu.stop_sequence if stu.HasField("stop_sequence") else None,
                    "arrival_delay": delay,
                    "schedule_relationship": sched_rel,
                })

    return pd.DataFrame(rows)


# === STOPS + JOIN Z VEHICLE POSITIONS ===

def add_stop_names_to_vehicles(vp_df: pd.DataFrame, stops_path: Path = STOPS_PATH) -> pd.DataFrame:
    """
    Łączy vehicle_positions z GTFS stops.txt po current_stop_id = stop_id.
    Zapewnia zgodne typy (oba jako string).
    """
    # stop_id jako string
    stops = pd.read_csv(stops_path, dtype={"stop_id": str})
    stops_small = stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]]

    vp_df = vp_df.copy()
    vp_df["current_stop_id"] = vp_df["current_stop_id"].astype(str)

    merged = vp_df.merge(
        stops_small,
        left_on="current_stop_id",
        right_on="stop_id",
        how="left",
    )

    merged = merged.rename(columns={
        "stop_name": "current_stop_name",
        "stop_lat": "current_stop_lat",
        "stop_lon": "current_stop_lon",
    }).drop(columns=["stop_id"])

    return merged

import math
import pandas as pd

def seconds_to_minutes_custom(sec):
    """
    Custom rounding:
    0–29 s -> floor
    30–59 s -> ceil
    działa też dla wartości ujemnych
    """
    if pd.isna(sec):
        return None
    
    sec = float(sec)
    minutes = int(sec // 60)  # część pełnych minut
    remainder = abs(sec % 60)  # sekundy reszty (zawsze dodatnie)

    if remainder < 30:
        return minutes
    else:
        # jeśli opóźnienie ujemne -> zaokrąglamy w dół (np. -70s -> -1, ale -40s -> 0)
        if sec < 0:
            return minutes - 1
        else:
            return minutes + 1
        

# === GŁÓWNY PIPELINE ===

def build_datasets_from_feeds(
    vehicle_feed: gtfs_realtime_pb2.FeedMessage,
    trip_feed: gtfs_realtime_pb2.FeedMessage,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    - parsuje feedy do DataFrame
    - dodaje nazwy przystanków do vehicles
    - dodaje route_type (tramwaj/autobus/nocny_autobus/unknown)
    - zwraca (vehicles_df, trips_df)
    NIE zapisuje nic na dysk.
    """

    # 1. Parsowanie feedów
    vp_df = parse_vehicle_positions_feed(vehicle_feed)
    tu_df = parse_trip_updates_feed(trip_feed)

    # 2. Nazwy przystanków
    vp_df = add_stop_names_to_vehicles(vp_df, STOPS_PATH)

    # 3. Typ linii
    vp_df["route_type"] = vp_df["route_id"].apply(classify_route_type)
    tu_df["route_type"] = tu_df["tu_route_id"].apply(classify_route_type)

    # 4. Końcowe kolumny
    vehicles_df = vp_df[
        [
            "entity_id",
            "trip_id",
            "route_id",
            "vehicle_id",
            "latitude",
            "longitude",
            "current_stop_id",
            "current_stop_name",
            "current_stop_sequence",
            "current_status",
            "route_type",
            "timestamp",
            "current_stop_lat",
            "current_stop_lon",
        ]
    ].copy()

    trips_df = tu_df[
        [
            "entity_id",
            "tu_trip_id",
            "tu_route_id",
            "tu_direction_id",
            "arrival_delay",
            "stop_id",
            "stop_sequence",
            "schedule_relationship",
            "route_type",
        ]
    ].copy()

    return vehicles_df, trips_df


def build_vehicles_trips_joined_from_feeds(
    vehicle_feed: gtfs_realtime_pb2.FeedMessage,
    trip_feed: gtfs_realtime_pb2.FeedMessage,
) -> pd.DataFrame:
    """
    Buduje JEDEN dataframe:
    - vehicles_df LEFT JOIN trips_df
    - join po (trip_id, current_stop_sequence) = (tu_trip_id, stop_sequence)
    - z trips dodajemy tylko kolumny, których nie ma w vehicles:
      tu_direction_id, arrival_delay, stop_id, stop_sequence, schedule_relationship
    """

    vehicles_df, trips_df = build_datasets_from_feeds(vehicle_feed, trip_feed)

    # tylko potrzebne kolumny z trips
    trips_small = trips_df[
        [
            "tu_trip_id",
            "stop_sequence",
            "tu_direction_id",
            "arrival_delay",
            "stop_id",
            "schedule_relationship",
        ]
    ].copy()

    # LEFT JOIN: vehicles  ⟵  trips
    merged = vehicles_df.merge(
        trips_small,
        left_on=["trip_id", "current_stop_sequence"],
        right_on=["tu_trip_id", "stop_sequence"],
        how="left",
        suffixes=("", "_trip"),
    )

    # tu_trip_id = trip_id → duplikat, więc wyrzucamy
    merged = merged.drop(columns=["tu_trip_id"])
    merged["arrival_delay_minutes"] = merged["arrival_delay"].apply(seconds_to_minutes_custom)

    # Możesz też wyrzucić stop_sequence z trips, jeśli nie chcesz duplikatu.
    # merged = merged.drop(columns=["stop_sequence"])

    return merged