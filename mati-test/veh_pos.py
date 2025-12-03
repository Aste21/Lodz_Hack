from google.transit import gtfs_realtime_pb2
import requests
import sqlite3
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request
import json

# Konfiguracja
URL = "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/vehicle_positions.bin"
DB_NAME = "vehicle_positions.db"
FETCH_INTERVAL = 10  # sekundy między pobraniami
API_PORT = 5000

# Globalne zmienne
app = Flask(__name__)
latest_response_data = None
db_lock = threading.Lock()


def init_database():
    """Inicjalizuje bazę danych SQLite"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicle_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT,
            trip_id TEXT,
            route_id TEXT,
            latitude REAL,
            longitude REAL,
            bearing REAL,
            speed REAL,
            timestamp INTEGER,
            feed_timestamp INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_vehicle_id ON vehicle_positions(vehicle_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON vehicle_positions(timestamp)
    ''')
    
    conn.commit()
    conn.close()
    print(f"Baza danych {DB_NAME} zainicjalizowana")


def save_to_database(feed, feed_timestamp):
    """Zapisuje dane z feed do bazy danych"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    saved_count = 0
    for entity in feed.entity:
        if entity.HasField("vehicle"):
            v = entity.vehicle
            vehicle_id = v.vehicle.id if v.vehicle.HasField("id") else None
            trip_id = v.trip.trip_id if v.trip.HasField("trip_id") else None
            route_id = v.trip.route_id if v.trip.HasField("route_id") else None
            latitude = v.position.latitude if v.position.HasField("latitude") else None
            longitude = v.position.longitude if v.position.HasField("longitude") else None
            bearing = v.position.bearing if v.position.HasField("bearing") else None
            speed = v.position.speed if v.position.HasField("speed") else None
            timestamp = v.timestamp if v.HasField("timestamp") else None
            
            cursor.execute('''
                INSERT INTO vehicle_positions 
                (vehicle_id, trip_id, route_id, latitude, longitude, bearing, speed, timestamp, feed_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (vehicle_id, trip_id, route_id, latitude, longitude, bearing, speed, timestamp, feed_timestamp))
            
            saved_count += 1
    
    conn.commit()
    conn.close()
    return saved_count


def fetch_vehicle_positions():
    """Pobiera dane z API i zapisuje do bazy"""
    global latest_response_data
    
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        feed_timestamp = feed.header.timestamp if feed.header.HasField("timestamp") else int(time.time())
        
        # Przygotuj sparsowane dane
        vehicles_data = []
        for entity in feed.entity:
            if entity.HasField("vehicle"):
                v = entity.vehicle
                vehicle_data = {
                    "vehicle_id": v.vehicle.id if v.vehicle.HasField("id") else None,
                    "trip_id": v.trip.trip_id if v.trip.HasField("trip_id") else None,
                    "route_id": v.trip.route_id if v.trip.HasField("route_id") else None,
                    "latitude": v.position.latitude if v.position.HasField("latitude") else None,
                    "longitude": v.position.longitude if v.position.HasField("longitude") else None,
                    "bearing": v.position.bearing if v.position.HasField("bearing") else None,
                    "speed": v.position.speed if v.position.HasField("speed") else None,
                    "timestamp": v.timestamp if v.HasField("timestamp") else None,
                }
                vehicles_data.append(vehicle_data)
        
        # Zapisz surowe dane response do zmiennej globalnej
        with db_lock:
            latest_response_data = {
                "raw_content_hex": response.content.hex(),  # Surowe dane jako hex string
                "feed_timestamp": feed_timestamp,
                "fetched_at": datetime.now().isoformat(),
                "header": {
                    "gtfs_realtime_version": feed.header.gtfs_realtime_version,
                    "timestamp": feed_timestamp
                },
                "vehicles": vehicles_data,
                "vehicle_count": len(vehicles_data)
            }
        
        # Zapisz do bazy danych
        saved_count = save_to_database(feed, feed_timestamp)
        
        # Printuj dane
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pobrano dane:")
        print(f"GTFS-RT header: {feed.header}")
        print(f"Liczba pojazdów: {len([e for e in feed.entity if e.HasField('vehicle')])}")
        print(f"Zapisano do bazy: {saved_count} pozycji")
        
        for entity in feed.entity:
            if entity.HasField("vehicle"):
                v = entity.vehicle
                print(f"Vehicle ID: {v.vehicle.id if v.vehicle.HasField('id') else 'N/A'}")
                print(f"Trip ID: {v.trip.trip_id if v.trip.HasField('trip_id') else 'N/A'}")
                print(f"Latitude: {v.position.latitude if v.position.HasField('latitude') else 'N/A'}")
                print(f"Longitude: {v.position.longitude if v.position.HasField('longitude') else 'N/A'}")
                print(f"Timestamp: {v.timestamp if v.HasField('timestamp') else 'N/A'}")
                print("---")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Błąd pobierania danych: {e}")
        return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Błąd przetwarzania: {e}")
        return False


def continuous_fetch_loop():
    """Pętla ciągłego pobierania danych"""
    print("Rozpoczynam ciągłe pobieranie danych...")
    while True:
        fetch_vehicle_positions()
        time.sleep(FETCH_INTERVAL)


@app.route('/api/vehicle_positions', methods=['GET'])
def get_vehicle_positions():
    """Endpoint API zwracający ostatni response"""
    try:
        with db_lock:
            if latest_response_data is None:
                return jsonify({
                    "error": "Brak danych",
                    "message": "Dane jeszcze nie zostały pobrane"
                }), 404
            
            # Create a copy without raw_content_hex to avoid large responses
            response_data = latest_response_data.copy()
            # Optionally include raw_content_hex only if requested via query param
            if 'include_raw' not in request.args:
                response_data.pop('raw_content_hex', None)
            
            return jsonify(response_data)
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/vehicle_positions/db', methods=['GET'])
def get_vehicle_positions_from_db():
    """Endpoint API zwracający dane z bazy danych"""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Pobierz ostatnie 100 pozycji
        cursor.execute('''
            SELECT * FROM vehicle_positions 
            ORDER BY created_at DESC 
            LIMIT 100
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        positions = [dict(row) for row in rows]
        
        return jsonify({
            "count": len(positions),
            "positions": positions
        })
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })


def run_api():
    """Uruchamia Flask API"""
    print(f"Uruchamiam API na porcie {API_PORT}...")
    try:
        app.run(host='0.0.0.0', port=API_PORT, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"Błąd uruchamiania API: {e}")


def main():
    """Główna funkcja"""
    # Inicjalizuj bazę danych
    init_database()
    
    # Pobierz dane raz na start
    print("Pobieram dane na start...")
    fetch_vehicle_positions()
    
    # Uruchom pętlę ciągłego pobierania w osobnym wątku
    fetch_thread = threading.Thread(target=continuous_fetch_loop, daemon=True)
    fetch_thread.start()
    
    # Uruchom API w głównym wątku (Flask nie działa dobrze w daemon thread)
    try:
        run_api()
    except KeyboardInterrupt:
        print("\nZatrzymywanie...")
        print(f"API dostępne pod: http://localhost:{API_PORT}/api/vehicle_positions")


if __name__ == "__main__":
    main()