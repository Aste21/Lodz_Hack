from google.transit import gtfs_realtime_pb2
import requests
import time
import os
from datetime import datetime

# Konfiguracja
ALERTS_URL = "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/alerts.bin"
VEHICLE_POSITIONS_URL = "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/vehicle_positions.bin"
FETCH_INTERVAL = 10  # sekundy między pobraniami
ALERTS_DIR = "saved_alerts"
VEHICLE_POSITIONS_DIR = "saved_vehicle_positions"

# Utwórz foldery jeśli nie istnieją
os.makedirs(ALERTS_DIR, exist_ok=True)
os.makedirs(VEHICLE_POSITIONS_DIR, exist_ok=True)

def fetch_alerts():
    """Pobiera alerty z API i zapisuje je jeśli są nowe"""
    try:
        response = requests.get(ALERTS_URL, timeout=10)
        response.raise_for_status()
        
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        feed_timestamp = feed.header.timestamp if feed.header.HasField("timestamp") else int(time.time())
        
        # Sprawdź czy są jakieś alerty
        alerts = [entity for entity in feed.entity if entity.HasField("alert")]
        
        if alerts:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ALERTS] Znaleziono {len(alerts)} alert(ów)!")
            
            # Zapisz surowe dane binarne do pliku
            timestamp_str = datetime.fromtimestamp(feed_timestamp).strftime('%Y%m%d_%H%M%S')
            filename = f"{ALERTS_DIR}/alerts_{timestamp_str}.bin"
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"Zapisano alerty do: {filename}")
            
            # Wyświetl informacje o alertach
            for i, entity in enumerate(alerts, 1):
                alert = entity.alert
                print(f"  Alert {i}:")
                print(f"    ID: {entity.id}")
                if alert.HasField("active_period"):
                    for period in alert.active_period:
                        start = period.start if period.HasField("start") else None
                        end = period.end if period.HasField("end") else None
                        print(f"    Okres aktywności: {start} - {end}")
                if alert.HasField("informed_entity"):
                    print(f"    Liczba powiadomionych encji: {len(alert.informed_entity)}")
                if alert.HasField("header_text"):
                    print(f"    Nagłówek: {alert.header_text.translation[0].text if alert.header_text.translation else 'N/A'}")
                print("    ---")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ALERTS] Brak alertów")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ALERTS] Błąd pobierania danych: {e}")
        return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ALERTS] Błąd przetwarzania: {e}")
        import traceback
        traceback.print_exc()
        return False


def fetch_vehicle_positions():
    """Pobiera vehicle_positions i zapisuje jeśli ma trip_update"""
    try:
        response = requests.get(VEHICLE_POSITIONS_URL, timeout=10)
        response.raise_for_status()
        
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        feed_timestamp = feed.header.timestamp if feed.header.HasField("timestamp") else int(time.time())
        
        # Sprawdź czy są encje z trip_update
        entities_with_trip_update = [entity for entity in feed.entity if entity.HasField("trip_update")]
        
        if entities_with_trip_update:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [VEHICLE_POSITIONS] Znaleziono {len(entities_with_trip_update)} encji z trip_update!")
            
            # Zapisz surowe dane binarne do pliku
            timestamp_str = datetime.fromtimestamp(feed_timestamp).strftime('%Y%m%d_%H%M%S')
            filename = f"{VEHICLE_POSITIONS_DIR}/vehicle_positions_{timestamp_str}.bin"
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"Zapisano vehicle_positions do: {filename}")
            
            # Wyświetl informacje o trip_updates
            for i, entity in enumerate(entities_with_trip_update, 1):
                trip_update = entity.trip_update
                print(f"  Trip Update {i}:")
                print(f"    ID: {entity.id}")
                if trip_update.HasField("trip"):
                    trip = trip_update.trip
                    print(f"    Trip ID: {trip.trip_id if trip.trip_id else 'N/A'}")
                    print(f"    Route ID: {trip.route_id if trip.route_id else 'N/A'}")
                if trip_update.HasField("vehicle"):
                    vehicle = trip_update.vehicle
                    print(f"    Vehicle ID: {vehicle.id if vehicle.id else 'N/A'}")
                print(f"    Stop time updates: {len(trip_update.stop_time_update)}")
                print("    ---")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [VEHICLE_POSITIONS] Brak encji z trip_update")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [VEHICLE_POSITIONS] Błąd pobierania danych: {e}")
        return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [VEHICLE_POSITIONS] Błąd przetwarzania: {e}")
        import traceback
        traceback.print_exc()
        return False


def continuous_fetch_loop():
    """Pętla ciągłego pobierania alertów i vehicle_positions"""
    print("Rozpoczynam monitorowanie alertów i vehicle_positions...")
    print(f"Alerts URL: {ALERTS_URL}")
    print(f"Vehicle Positions URL: {VEHICLE_POSITIONS_URL}")
    print(f"Interwał: {FETCH_INTERVAL} sekund")
    print(f"Foldery zapisu: {ALERTS_DIR}/, {VEHICLE_POSITIONS_DIR}/")
    print("-" * 50)
    
    while True:
        fetch_alerts()
        fetch_vehicle_positions()
        time.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    try:
        continuous_fetch_loop()
    except KeyboardInterrupt:
        print("\n\nZatrzymywanie monitora alertów...")

