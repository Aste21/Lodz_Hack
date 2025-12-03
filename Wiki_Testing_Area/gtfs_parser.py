"""
Parser i interpreter danych GTFS dla komunikacji miejskiej w Łodzi
GTFS (General Transit Feed Specification) - standardowy format danych o transporcie publicznym
"""

import pandas as pd
import os
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class GTFSReader:
    """Klasa do czytania i interpretacji danych GTFS"""
    
    def __init__(self, gtfs_dir: Optional[str] = None):
        """
        Inicjalizacja parsera GTFS
        
        Args:
            gtfs_dir: Ścieżka do folderu z plikami GTFS (domyślnie automatycznie wykrywa)
        """
        if gtfs_dir is None:
            # Automatyczne wykrywanie folderu GTFS względem lokalizacji skryptu
            script_dir = Path(__file__).parent
            self.gtfs_dir = script_dir / "GTFS"
            # Jeśli nie ma w tym samym folderze, spróbuj względem bieżącego katalogu
            if not self.gtfs_dir.exists():
                self.gtfs_dir = Path("GTFS")
        else:
            self.gtfs_dir = Path(gtfs_dir)
        
        self.data = {}
        self.loaded = False
        
    def load_all(self):
        """Ładuje wszystkie pliki GTFS do pamięci"""
        print("Ładowanie danych GTFS...")
        print(f"  Szukam plików w: {self.gtfs_dir.absolute()}")
        
        # Lista plików GTFS do załadowania
        files_to_load = {
            'agency': 'agency.txt',
            'stops': 'stops.txt',
            'routes': 'routes.txt',
            'trips': 'trips.txt',
            'stop_times': 'stop_times.txt',
            'calendar': 'calendar.txt',
            'calendar_dates': 'calendar_dates.txt',
            'shapes': 'shapes.txt',
            'feed_info': 'feed_info.txt'
        }
        
        for key, filename in files_to_load.items():
            filepath = self.gtfs_dir / filename
            if filepath.exists():
                try:
                    print(f"  Ładowanie {filename}...")
                    self.data[key] = pd.read_csv(filepath, low_memory=False)
                    print(f"    ✓ Załadowano {len(self.data[key])} rekordów")
                except Exception as e:
                    print(f"    ✗ Błąd przy ładowaniu {filename}: {e}")
            else:
                print(f"    ⚠ Plik {filename} nie istnieje (szukano: {filepath.absolute()})")
        
        self.loaded = True
        print("\n✓ Wszystkie dane załadowane!\n")
        
    def get_agency_info(self) -> Dict:
        """Zwraca informacje o agencji transportowej"""
        if 'agency' not in self.data:
            return {}
        
        agency = self.data['agency'].iloc[0]
        return {
            'name': agency.get('agency_name', ''),
            'url': agency.get('agency_url', ''),
            'timezone': agency.get('agency_timezone', ''),
            'phone': agency.get('agency_phone', ''),
            'email': agency.get('agency_email', '')
        }
    
    def get_stop_info(self, stop_id: int) -> Optional[Dict]:
        """Zwraca informacje o przystanku"""
        if 'stops' not in self.data:
            return None
        
        stop = self.data['stops'][self.data['stops']['stop_id'] == stop_id]
        if stop.empty:
            return None
        
        stop = stop.iloc[0]
        return {
            'stop_id': stop['stop_id'],
            'stop_code': stop.get('stop_code', ''),
            'stop_name': stop.get('stop_name', ''),
            'stop_lat': stop.get('stop_lat', None),
            'stop_lon': stop.get('stop_lon', None),
            'wheelchair_boarding': stop.get('wheelchair_boarding', 0)
        }
    
    def get_route_info(self, route_id: str) -> Optional[Dict]:
        """Zwraca informacje o linii"""
        if 'routes' not in self.data:
            return None
        
        route = self.data['routes'][self.data['routes']['route_id'] == route_id]
        if route.empty:
            return None
        
        route = route.iloc[0]
        return {
            'route_id': route['route_id'],
            'route_short_name': route.get('route_short_name', ''),
            'route_long_name': route.get('route_long_name', ''),
            'route_type': route.get('route_type', 0),
            'route_color': route.get('route_color', ''),
            'route_text_color': route.get('route_text_color', '')
        }
    
    def get_trips_for_route(self, route_id: str) -> pd.DataFrame:
        """Zwraca wszystkie kursy dla danej linii"""
        if 'trips' not in self.data:
            return pd.DataFrame()
        
        return self.data['trips'][self.data['trips']['route_id'] == route_id]
    
    def get_stop_times_for_trip(self, trip_id: str) -> pd.DataFrame:
        """Zwraca wszystkie przystanki dla danego kursu"""
        if 'stop_times' not in self.data:
            return pd.DataFrame()
        
        trip_stops = self.data['stop_times'][self.data['stop_times']['trip_id'] == trip_id]
        return trip_stops.sort_values('stop_sequence')
    
    def get_trip_details(self, trip_id: str) -> Optional[Dict]:
        """Zwraca szczegółowe informacje o kursie wraz z przystankami"""
        if 'trips' not in self.data or 'stop_times' not in self.data:
            return None
        
        trip = self.data['trips'][self.data['trips']['trip_id'] == trip_id]
        if trip.empty:
            return None
        
        trip = trip.iloc[0]
        stop_times = self.get_stop_times_for_trip(trip_id)
        
        stops_info = []
        for _, stop_time in stop_times.iterrows():
            stop_info = self.get_stop_info(stop_time['stop_id'])
            stops_info.append({
                'stop_id': stop_time['stop_id'],
                'stop_name': stop_info['stop_name'] if stop_info else 'Nieznany',
                'arrival_time': stop_time['arrival_time'],
                'departure_time': stop_time['departure_time'],
                'stop_sequence': stop_time['stop_sequence']
            })
        
        return {
            'trip_id': trip_id,
            'route_id': trip['route_id'],
            'trip_headsign': trip.get('trip_headsign', ''),
            'direction_id': trip.get('direction_id', None),
            'service_id': trip.get('service_id', ''),
            'stops': stops_info
        }
    
    def find_stops_by_name(self, name_pattern: str) -> pd.DataFrame:
        """Znajduje przystanki po nazwie (wzorzec)"""
        if 'stops' not in self.data:
            return pd.DataFrame()
        
        pattern = name_pattern.lower()
        stops = self.data['stops']
        mask = stops['stop_name'].str.lower().str.contains(pattern, na=False)
        return stops[mask]
    
    def get_routes_summary(self) -> pd.DataFrame:
        """Zwraca podsumowanie wszystkich linii"""
        if 'routes' not in self.data:
            return pd.DataFrame()
        
        routes = self.data['routes'].copy()
        
        # Dodaj liczbę kursów dla każdej linii
        if 'trips' in self.data:
            trip_counts = self.data['trips']['route_id'].value_counts()
            routes['trip_count'] = routes['route_id'].map(trip_counts).fillna(0).astype(int)
        else:
            routes['trip_count'] = 0
        
        return routes[['route_id', 'route_short_name', 'route_long_name', 
                       'route_type', 'trip_count']].sort_values('route_short_name')
    
    def get_stops_near_location(self, lat: float, lon: float, radius_km: float = 1.0) -> pd.DataFrame:
        """
        Znajduje przystanki w pobliżu danej lokalizacji
        
        Args:
            lat: Szerokość geograficzna
            lon: Długość geograficzna
            radius_km: Promień w kilometrach (domyślnie 1 km)
        
        Returns:
            DataFrame z przystankami posortowanymi według odległości
        """
        if 'stops' not in self.data:
            return pd.DataFrame()
        
        stops = self.data['stops'].copy()
        
        # Oblicz odległość (uproszczony wzór Haversine)
        import math
        
        def calculate_distance(lat1, lon1, lat2, lon2):
            R = 6371  # Promień Ziemi w km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat/2)**2 + 
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
                 math.sin(dlon/2)**2)
            c = 2 * math.asin(math.sqrt(a))
            return R * c
        
        stops['distance_km'] = stops.apply(
            lambda row: calculate_distance(lat, lon, row['stop_lat'], row['stop_lon']),
            axis=1
        )
        
        nearby = stops[stops['distance_km'] <= radius_km]
        return nearby.sort_values('distance_km')
    
    def get_departures_from_stop(self, stop_id: int, time_str: Optional[str] = None) -> pd.DataFrame:
        """
        Zwraca wszystkie odjazdy z danego przystanku
        
        Args:
            stop_id: ID przystanku
            time_str: Czas w formacie HH:MM:SS (opcjonalnie, domyślnie wszystkie)
        """
        if 'stop_times' not in self.data or 'trips' not in self.data:
            return pd.DataFrame()
        
        # Znajdź wszystkie odjazdy z przystanku
        stop_times = self.data['stop_times'][self.data['stop_times']['stop_id'] == stop_id]
        
        # Połącz z informacjami o kursach
        departures = stop_times.merge(
            self.data['trips'][['trip_id', 'route_id', 'trip_headsign', 'direction_id']],
            on='trip_id',
            how='left'
        )
        
        # Połącz z informacjami o liniach
        if 'routes' in self.data:
            departures = departures.merge(
                self.data['routes'][['route_id', 'route_short_name', 'route_long_name']],
                on='route_id',
                how='left'
            )
        
        # Filtruj po czasie jeśli podano
        if time_str:
            departures = departures[departures['departure_time'] >= time_str]
        
        # Sortuj po czasie odjazdu
        departures = departures.sort_values('departure_time')
        
        return departures[['departure_time', 'route_short_name', 'trip_headsign', 
                          'direction_id', 'trip_id']].head(50)  # Limit do 50 wyników
    
    def get_statistics(self) -> Dict:
        """Zwraca statystyki o danych GTFS"""
        stats = {}
        
        if 'stops' in self.data:
            stats['total_stops'] = len(self.data['stops'])
        
        if 'routes' in self.data:
            stats['total_routes'] = len(self.data['routes'])
            # Podział na typy linii
            if 'route_type' in self.data['routes']:
                stats['routes_by_type'] = self.data['routes']['route_type'].value_counts().to_dict()
        
        if 'trips' in self.data:
            stats['total_trips'] = len(self.data['trips'])
        
        if 'stop_times' in self.data:
            stats['total_stop_times'] = len(self.data['stop_times'])
        
        if 'calendar' in self.data:
            stats['total_services'] = len(self.data['calendar'])
        
        return stats


def main():
    """Przykładowe użycie parsera GTFS"""
    
    # Inicjalizacja parsera (automatycznie znajdzie folder GTFS)
    parser = GTFSReader()
    parser.load_all()
    
    # Wyświetl informacje o agencji
    print("=" * 60)
    print("INFORMACJE O AGENCJI")
    print("=" * 60)
    agency = parser.get_agency_info()
    for key, value in agency.items():
        print(f"{key}: {value}")
    
    # Statystyki
    print("\n" + "=" * 60)
    print("STATYSTYKI")
    print("=" * 60)
    stats = parser.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Podsumowanie linii
    print("\n" + "=" * 60)
    print("PODSUMOWANIE LINII (pierwsze 20)")
    print("=" * 60)
    routes_summary = parser.get_routes_summary()
    print(routes_summary.head(20).to_string(index=False))
    
    # Przykład: znajdź przystanki z "Centrum" w nazwie
    print("\n" + "=" * 60)
    print("PRZYSTANKI Z 'CENTRUM' W NAZWIE")
    print("=" * 60)
    centrum_stops = parser.find_stops_by_name("Centrum")
    if not centrum_stops.empty:
        print(centrum_stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']].head(10).to_string(index=False))
    
    # Przykład: przystanki w pobliżu centrum Łodzi (około 51.77, 19.46)
    print("\n" + "=" * 60)
    print("PRZYSTANKI W POBLIŻU CENTRUM ŁODZI (1 km)")
    print("=" * 60)
    nearby_stops = parser.get_stops_near_location(51.77, 19.46, radius_km=1.0)
    if not nearby_stops.empty:
        print(nearby_stops[['stop_id', 'stop_name', 'distance_km']].head(10).to_string(index=False))
    
    # Przykład: szczegóły kursu
    print("\n" + "=" * 60)
    print("PRZYKŁAD: SZCZEGÓŁY KURSU")
    print("=" * 60)
    if 'trips' in parser.data and len(parser.data['trips']) > 0:
        sample_trip_id = parser.data['trips'].iloc[0]['trip_id']
        trip_details = parser.get_trip_details(sample_trip_id)
        if trip_details:
            print(f"Kurs: {trip_details['trip_id']}")
            print(f"Linia: {trip_details['route_id']}")
            print(f"Kierunek: {trip_details['trip_headsign']}")
            print(f"\nPrzystanki (pierwsze 5):")
            for stop in trip_details['stops'][:5]:
                print(f"  {stop['stop_sequence']}. {stop['stop_name']} - {stop['departure_time']}")


if __name__ == "__main__":
    main()

