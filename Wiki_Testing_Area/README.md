# Parser danych GTFS - Komunikacja Miejska Łódź

Narzędzie do interpretacji i analizy danych GTFS (General Transit Feed Specification) dla komunikacji miejskiej w Łodzi.

## Instalacja

```bash
pip install -r requirements.txt
```

## Struktura danych GTFS

Dane GTFS zawierają następujące pliki:
- `agency.txt` - informacje o operatorze transportu
- `stops.txt` - przystanki (2412 przystanków)
- `routes.txt` - linie komunikacyjne (132 linie)
- `trips.txt` - kursy (47695 kursów)
- `stop_times.txt` - czasy przyjazdów/odjazdów (1351605 rekordów)
- `calendar.txt` - kalendarz kursów
- `calendar_dates.txt` - wyjątki w kalendarzu
- `shapes.txt` - kształty tras
- `feed_info.txt` - informacje o danych

## Użycie

### Podstawowe użycie

```python
from gtfs_parser import GTFSReader

# Inicjalizacja parsera
parser = GTFSReader("GTFS")
parser.load_all()

# Pobierz informacje o agencji
agency = parser.get_agency_info()
print(agency)

# Pobierz statystyki
stats = parser.get_statistics()
print(stats)
```

### Przykłady zapytań

#### 1. Znajdź przystanki po nazwie
```python
stops = parser.find_stops_by_name("Centrum")
print(stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']])
```

#### 2. Znajdź przystanki w pobliżu lokalizacji
```python
# Przystanki w promieniu 1 km od centrum Łodzi
nearby = parser.get_stops_near_location(51.77, 19.46, radius_km=1.0)
print(nearby[['stop_name', 'distance_km']])
```

#### 3. Pobierz informacje o przystanku
```python
stop_info = parser.get_stop_info(543)  # Piotrkowska Centrum
print(stop_info)
```

#### 4. Pobierz informacje o linii
```python
route_info = parser.get_route_info("1")
print(route_info)
```

#### 5. Pobierz wszystkie kursy dla linii
```python
trips = parser.get_trips_for_route("1")
print(trips[['trip_id', 'trip_headsign', 'direction_id']])
```

#### 6. Pobierz szczegóły kursu z przystankami
```python
trip_details = parser.get_trip_details("11311_1")
for stop in trip_details['stops']:
    print(f"{stop['stop_sequence']}. {stop['stop_name']} - {stop['departure_time']}")
```

#### 7. Pobierz odjazdy z przystanku
```python
# Wszystkie odjazdy z przystanku
departures = parser.get_departures_from_stop(543)

# Odjazdy po określonej godzinie
departures = parser.get_departures_from_stop(543, time_str="08:00:00")
print(departures)
```

#### 8. Podsumowanie wszystkich linii
```python
routes_summary = parser.get_routes_summary()
print(routes_summary)
```

## Uruchomienie przykładowego skryptu

```bash
python3 gtfs_parser.py
```

## Statystyki danych

- **Przystanki**: 2412
- **Linie**: 132 (25 tramwajów, 107 autobusów)
- **Kursy**: 47695
- **Rekordy czasów**: 1351605

## Typy linii (route_type)

- `0` - Tramwaj
- `3` - Autobus

## Autor

Parser stworzony dla danych ZDiT (Zarząd Dróg i Transportu w Łodzi)

