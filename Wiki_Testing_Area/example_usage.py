"""
Przykłady użycia parsera GTFS
"""

from gtfs_parser import GTFSReader


def example_1_basic_info():
    """Przykład 1: Podstawowe informacje"""
    print("\n" + "="*60)
    print("PRZYKŁAD 1: Podstawowe informacje")
    print("="*60)
    
    parser = GTFSReader()
    parser.load_all()
    
    # Informacje o agencji
    agency = parser.get_agency_info()
    print(f"\nAgencja: {agency['name']}")
    print(f"Strona: {agency['url']}")
    print(f"Email: {agency['email']}")
    
    # Statystyki
    stats = parser.get_statistics()
    print(f"\nStatystyki:")
    print(f"  Przystanki: {stats['total_stops']}")
    print(f"  Linie: {stats['total_routes']}")
    print(f"  Kursy: {stats['total_trips']}")
    print(f"  Typy linii: {stats['routes_by_type']}")


def example_2_find_stops():
    """Przykład 2: Wyszukiwanie przystanków"""
    print("\n" + "="*60)
    print("PRZYKŁAD 2: Wyszukiwanie przystanków")
    print("="*60)
    
    parser = GTFSReader()
    parser.load_all()
    
    # Znajdź przystanki z "Dworzec" w nazwie
    stops = parser.find_stops_by_name("Dworzec")
    print(f"\nZnaleziono {len(stops)} przystanków z 'Dworzec' w nazwie:")
    for _, stop in stops.head(10).iterrows():
        print(f"  {stop['stop_id']}: {stop['stop_name']}")


def example_3_nearby_stops():
    """Przykład 3: Przystanki w pobliżu"""
    print("\n" + "="*60)
    print("PRZYKŁAD 3: Przystanki w pobliżu lokalizacji")
    print("="*60)
    
    parser = GTFSReader()
    parser.load_all()
    
    # Centrum Łodzi (około Piotrkowska Centrum)
    lat, lon = 51.75924, 19.45762
    radius = 0.5  # 500 metrów
    
    nearby = parser.get_stops_near_location(lat, lon, radius_km=radius)
    print(f"\nPrzystanki w promieniu {radius} km:")
    for _, stop in nearby.head(10).iterrows():
        print(f"  {stop['stop_name']} - {stop['distance_km']:.3f} km")


def example_4_route_details():
    """Przykład 4: Szczegóły linii"""
    print("\n" + "="*60)
    print("PRZYKŁAD 4: Szczegóły linii")
    print("="*60)
    
    parser = GTFSReader()
    parser.load_all()
    
    # Informacje o linii 1
    route = parser.get_route_info("1")
    if route:
        print(f"\nLinia: {route['route_short_name']}")
        print(f"Typ: {'Tramwaj' if route['route_type'] == 0 else 'Autobus'}")
    
    # Wszystkie kursy linii 1
    trips = parser.get_trips_for_route("1")
    print(f"\nLiczba kursów linii 1: {len(trips)}")
    print("\nPrzykładowe kursy:")
    for _, trip in trips.head(5).iterrows():
        print(f"  {trip['trip_id']}: {trip['trip_headsign']}")


def example_5_trip_details():
    """Przykład 5: Szczegóły kursu"""
    print("\n" + "="*60)
    print("PRZYKŁAD 5: Szczegóły kursu")
    print("="*60)
    
    parser = GTFSReader()
    parser.load_all()
    
    # Pobierz pierwszy kurs linii 1
    trips = parser.get_trips_for_route("1")
    if not trips.empty:
        trip_id = trips.iloc[0]['trip_id']
        trip_details = parser.get_trip_details(trip_id)
        
        if trip_details:
            print(f"\nKurs: {trip_details['trip_id']}")
            print(f"Linia: {trip_details['route_id']}")
            print(f"Kierunek: {trip_details['trip_headsign']}")
            print(f"\nTrasa (wszystkie przystanki):")
            for stop in trip_details['stops']:
                print(f"  {stop['stop_sequence']:2d}. {stop['stop_name']:40s} - {stop['departure_time']}")


def example_6_departures():
    """Przykład 6: Odjazdy z przystanku"""
    print("\n" + "="*60)
    print("PRZYKŁAD 6: Odjazdy z przystanku")
    print("="*60)
    
    parser = GTFSReader()
    parser.load_all()
    
    # Znajdź przystanek "Piotrkowska Centrum"
    stops = parser.find_stops_by_name("Piotrkowska Centrum")
    if not stops.empty:
        stop_id = stops.iloc[0]['stop_id']
        stop_info = parser.get_stop_info(stop_id)
        
        print(f"\nPrzystanek: {stop_info['stop_name']} (ID: {stop_id})")
        
        # Odjazdy po 8:00
        departures = parser.get_departures_from_stop(stop_id, time_str="08:00:00")
        print(f"\nOdjazdy po 08:00 (pierwsze 10):")
        for _, dep in departures.head(10).iterrows():
            print(f"  {dep['departure_time']} - Linia {dep['route_short_name']} - {dep['trip_headsign']}")


def example_7_routes_summary():
    """Przykład 7: Podsumowanie linii"""
    print("\n" + "="*60)
    print("PRZYKŁAD 7: Podsumowanie linii")
    print("="*60)
    
    parser = GTFSReader()
    parser.load_all()
    
    routes = parser.get_routes_summary()
    
    # Linie tramwajowe
    trams = routes[routes['route_type'] == 0]
    print(f"\nLinie tramwajowe: {len(trams)}")
    print(f"Średnia liczba kursów na linię: {trams['trip_count'].mean():.0f}")
    
    # Linie autobusowe
    buses = routes[routes['route_type'] == 3]
    print(f"\nLinie autobusowe: {len(buses)}")
    print(f"Średnia liczba kursów na linię: {buses['trip_count'].mean():.0f}")
    
    # Linie z największą liczbą kursów
    print("\nTop 10 linii z największą liczbą kursów:")
    top_routes = routes.nlargest(10, 'trip_count')
    for _, route in top_routes.iterrows():
        route_type = "Tramwaj" if route['route_type'] == 0 else "Autobus"
        print(f"  Linia {route['route_short_name']:5s} ({route_type:8s}): {route['trip_count']:4d} kursów")


if __name__ == "__main__":
    # Uruchom wszystkie przykłady
    example_1_basic_info()
    example_2_find_stops()
    example_3_nearby_stops()
    example_4_route_details()
    example_5_trip_details()
    example_6_departures()
    example_7_routes_summary()
    
    print("\n" + "="*60)
    print("Wszystkie przykłady zakończone!")
    print("="*60)

