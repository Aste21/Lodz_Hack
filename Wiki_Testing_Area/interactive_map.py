"""
Interaktywna mapa Łodzi z pozycjami pojazdów i przystankami
Używa OpenStreetMap jako głównej warstwy mapy
"""

import pandas as pd
import folium
from folium import plugins
from pathlib import Path
from typing import Optional, Dict
from gtfs_parser import GTFSReader


class LodzTransitMap:
    """Klasa do tworzenia interaktywnej mapy komunikacji miejskiej w Łodzi"""
    
    def __init__(self):
        self.gtfs_parser = GTFSReader()
        self.gtfs_parser.load_all()
        self.vehicle_positions = None
        self.map = None
        
    def load_vehicle_positions(self, vehicle_positions_file: Optional[str] = None):
        """Ładuje pozycje pojazdów z pliku CSV"""
        if vehicle_positions_file is None:
            vehicle_positions_file = "bin_csv_output/vehicle_positions_vehicle_positions.csv"
        
        filepath = Path(__file__).parent / vehicle_positions_file
        if filepath.exists():
            self.vehicle_positions = pd.read_csv(filepath)
            print(f"✓ Załadowano {len(self.vehicle_positions)} pozycji pojazdów")
        else:
            print(f"⚠ Plik {vehicle_positions_file} nie istnieje")
            self.vehicle_positions = pd.DataFrame()
    
    def create_map(self, center_lat: float = 51.759, center_lon: float = 19.456, zoom_start: int = 12):
        """Tworzy interaktywną mapę używając OpenStreetMap"""
        # Centrum Łodzi
        # Używamy OpenStreetMap jako głównej warstwy
        self.map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles='OpenStreetMap',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        )
        
        # Dodaj alternatywne warstwy OpenStreetMap
        # Standardowa warstwa OSM
        folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            name='OpenStreetMap (Standard)',
            overlay=False,
            control=True
        ).add_to(self.map)
        
        # OSM Humanitarian (dobra dla transportu)
        folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Tiles style by <a href="https://www.hotosm.org/" target="_blank">HOT</a>',
            name='OpenStreetMap Humanitarian',
            overlay=False,
            control=True
        ).add_to(self.map)
        
        # OSM DE (Niemiecka wersja, często ma lepsze dane dla Polski)
        folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.de/{z}/{x}/{y}.png',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            name='OpenStreetMap DE',
            overlay=False,
            control=True
        ).add_to(self.map)
        
        # Dodaj też alternatywne warstwy dla porównania
        folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(self.map)
        folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(self.map)
        
        return self.map
    
    def add_stops(self, show_all: bool = True, route_filter: Optional[str] = None, use_clustering: bool = True):
        """Dodaje przystanki na mapę"""
        if 'stops' not in self.gtfs_parser.data:
            print("⚠ Brak danych o przystankach")
            return
        
        stops = self.gtfs_parser.data['stops'].copy()
        
        # Filtruj po linii jeśli podano
        if route_filter and self.vehicle_positions is not None and not self.vehicle_positions.empty:
            # Znajdź przystanki używane przez pojazdy danej linii
            route_vehicles = self.vehicle_positions[self.vehicle_positions['route_id'] == route_filter]
            if not route_vehicles.empty:
                # Możemy dodać logikę filtrowania przystanków po linii
                pass
        
        # Ogranicz liczbę przystanków jeśli pokazujemy wszystkie (dla wydajności)
        if show_all and len(stops) > 1000:
            # Pokaż co 2 przystanek dla lepszej wydajności
            stops = stops.iloc[::2]
            print(f"  Pokazuję {len(stops)} przystanków (co drugi dla wydajności)")
        
        # Usuń przystanki bez współrzędnych
        stops = stops.dropna(subset=['stop_lat', 'stop_lon'])
        
        # Użyj klastrowania dla lepszej wydajności
        if use_clustering and len(stops) > 100:
            stops_group = plugins.MarkerCluster(name='Przystanki', show=True)
            print(f"  Używam klastrowania markerów dla {len(stops)} przystanków")
        else:
            stops_group = folium.FeatureGroup(name='Przystanki', show=True)
        
        for _, stop in stops.iterrows():
            # Ikona przystanku
            icon = folium.Icon(
                icon='map-marker',
                prefix='fa',
                color='blue',
                icon_color='white'
            )
            
            # Popup z informacjami
            popup_html = f"""
            <div style="font-family: Arial; min-width: 200px;">
                <h4 style="margin: 5px 0; color: #0066cc;">{stop['stop_name']}</h4>
                <hr style="margin: 5px 0;">
                <p style="margin: 3px 0;"><b>ID:</b> {stop['stop_id']}</p>
                <p style="margin: 3px 0;"><b>Kod:</b> {stop.get('stop_code', 'N/A')}</p>
            </div>
            """
            
            folium.Marker(
                location=[stop['stop_lat'], stop['stop_lon']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=stop['stop_name'],
                icon=icon
            ).add_to(stops_group)
        
        stops_group.add_to(self.map)
        print(f"✓ Dodano {len(stops)} przystanków na mapę")
    
    def add_vehicles(self, route_filter: Optional[str] = None, use_clustering: bool = False):
        """Dodaje pozycje pojazdów na mapę"""
        if self.vehicle_positions is None or self.vehicle_positions.empty:
            print("⚠ Brak danych o pozycjach pojazdów")
            return
        
        vehicles = self.vehicle_positions.copy()
        
        # Filtruj po linii jeśli podano
        if route_filter:
            vehicles = vehicles[vehicles['route_id'] == route_filter]
            print(f"  Filtrowanie po linii: {route_filter}")
        
        # Usuń pojazdy bez współrzędnych
        vehicles = vehicles.dropna(subset=['latitude', 'longitude'])
        
        if vehicles.empty:
            print("⚠ Brak pojazdów do wyświetlenia")
            return
        
        # Kolory dla różnych typów linii
        def get_route_color(route_type: Optional[int], route_id: str) -> str:
            if route_type == 0:  # Tramwaj
                return 'red'
            elif route_type == 3:  # Autobus
                return 'green'
            else:
                return 'orange'
        
        # Pobierz typy linii
        if 'routes' in self.gtfs_parser.data:
            routes_info = self.gtfs_parser.data['routes'].set_index('route_id')
        
        # Użyj klastrowania jeśli dużo pojazdów
        if use_clustering and len(vehicles) > 50:
            vehicles_group = plugins.MarkerCluster(name='Pojazdy', show=True)
        else:
            vehicles_group = folium.FeatureGroup(name='Pojazdy', show=True)
        
        # Status pojazdu
        status_map = {
            0: 'W drodze do przystanku',
            1: 'Zatrzymany na przystanku',
            2: 'W drodze',
            3: 'Zatrzymany'
        }
        
        for _, vehicle in vehicles.iterrows():
            route_id = str(vehicle.get('route_id', 'N/A'))
            
            # Określ kolor na podstawie typu linii
            route_type = None
            if 'routes' in self.gtfs_parser.data:
                route_info = routes_info.get(route_id)
                if route_info is not None:
                    route_type = route_info.get('route_type')
            
            color = get_route_color(route_type, route_id)
            
            # Ikona pojazdu - użyj różnych ikon dla tramwajów i autobusów
            if route_type == 0:  # Tramwaj
                icon_name = 'train'
            else:  # Autobus
                icon_name = 'bus'
            
            icon = folium.Icon(
                icon=icon_name,
                prefix='fa',
                color=color,
                icon_color='white'
            )
            
            current_status = status_map.get(vehicle.get('current_status', 0), 'Nieznany')
            
            # Prędkość
            speed = vehicle.get('speed', 0)
            speed_kmh = speed * 3.6 if pd.notna(speed) else 0  # m/s -> km/h
            
            # Pobierz nazwę przystanku jeśli możliwe
            stop_id = vehicle.get('current_stop_id')
            stop_name = 'N/A'
            if pd.notna(stop_id) and 'stops' in self.gtfs_parser.data:
                stop_info = self.gtfs_parser.get_stop_info(int(stop_id))
                if stop_info:
                    stop_name = stop_info['stop_name']
            
            # Popup z informacjami
            popup_html = f"""
            <div style="font-family: Arial; min-width: 280px;">
                <h4 style="margin: 5px 0; color: {color};">
                    <i class="fa fa-{icon_name}" style="color: {color};"></i> Linia {route_id}
                </h4>
                <hr style="margin: 5px 0;">
                <p style="margin: 3px 0;"><b>Pojazd ID:</b> {vehicle.get('vehicle_id', 'N/A')}</p>
                <p style="margin: 3px 0;"><b>Kurs:</b> {vehicle.get('trip_id', 'N/A')}</p>
                <p style="margin: 3px 0;"><b>Status:</b> {current_status}</p>
                <p style="margin: 3px 0;"><b>Prędkość:</b> {speed_kmh:.1f} km/h</p>
                <p style="margin: 3px 0;"><b>Przystanek:</b> {stop_name} (ID: {stop_id if pd.notna(stop_id) else 'N/A'})</p>
            </div>
            """
            
            folium.Marker(
                location=[vehicle['latitude'], vehicle['longitude']],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"Linia {route_id} - Pojazd {vehicle.get('vehicle_id', 'N/A')}",
                icon=icon
            ).add_to(vehicles_group)
        
        vehicles_group.add_to(self.map)
        print(f"✓ Dodano {len(vehicles)} pojazdów na mapę")
    
    def add_route_filter_control(self):
        """Dodaje kontrolkę do filtrowania po liniach"""
        if self.vehicle_positions is None or self.vehicle_positions.empty:
            return
        
        # Pobierz unikalne linie
        routes = sorted(self.vehicle_positions['route_id'].dropna().unique())
        
        # HTML dla kontrolki
        html = """
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 200px; height: auto; 
                    background-color: white; z-index:9999; 
                    padding: 10px; border: 2px solid grey; border-radius: 5px;
                    font-family: Arial; font-size: 12px;">
            <h4 style="margin-top: 0;">Filtruj po linii:</h4>
            <select id="routeSelect" onchange="filterRoute()" style="width: 100%;">
                <option value="">Wszystkie linie</option>
        """
        
        for route in routes:
            html += f'<option value="{route}">Linia {route}</option>\n'
        
        html += """
            </select>
            <p style="font-size: 10px; color: #666;">Wybierz linię aby zobaczyć tylko jej pojazdy</p>
        </div>
        <script>
            function filterRoute() {
                var route = document.getElementById('routeSelect').value;
                // Ta funkcja wymagałaby odświeżenia mapy - uproszczona wersja
                console.log('Wybrana linia:', route);
            }
        </script>
        """
        
        self.map.get_root().html.add_child(folium.Element(html))
    
    def add_legend(self):
        """Dodaje legendę do mapy"""
        legend_html = """
        <div style="position: fixed; 
                    bottom: 50px; right: 10px; width: 220px; height: auto; 
                    background-color: white; z-index:9999; 
                    padding: 15px; border: 2px solid #333; border-radius: 8px;
                    font-family: Arial; font-size: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
            <h4 style="margin-top: 0; color: #333;">Legenda:</h4>
            <hr style="margin: 8px 0;">
            <p style="margin: 5px 0;"><i class="fa fa-map-marker" style="color: blue; font-size: 16px;"></i> <b>Przystanki</b></p>
            <p style="margin: 5px 0;"><i class="fa fa-train" style="color: red; font-size: 16px;"></i> <b>Tramwaje</b></p>
            <p style="margin: 5px 0;"><i class="fa fa-bus" style="color: green; font-size: 16px;"></i> <b>Autobusy</b></p>
            <p style="margin: 5px 0;"><i class="fa fa-bus" style="color: orange; font-size: 16px;"></i> <b>Inne pojazdy</b></p>
            <hr style="margin: 8px 0;">
            <p style="font-size: 10px; color: #666; margin: 5px 0;">
                Kliknij na marker aby zobaczyć szczegóły
            </p>
        </div>
        """
        self.map.get_root().html.add_child(folium.Element(legend_html))
    
    def save_map(self, filename: str = "lodz_transit_map.html"):
        """Zapisuje mapę do pliku HTML"""
        if self.map is None:
            print("⚠ Najpierw utwórz mapę używając create_map()")
            return
        
        # Dodaj kontrolkę warstw
        folium.LayerControl().add_to(self.map)
        
        # Dodaj legendę
        self.add_legend()
        
        # Zapisz
        filepath = Path(__file__).parent / filename
        self.map.save(str(filepath))
        print(f"✓ Mapa zapisana do: {filepath}")
        print(f"  Otwórz plik w przeglądarce aby zobaczyć interaktywną mapę")


def main():
    """Główna funkcja"""
    print("=" * 60)
    print("TWORZENIE INTERAKTYWNEJ MAPY ŁODZI")
    print("=" * 60)
    
    # Utwórz mapę
    map_creator = LodzTransitMap()
    
    # Załaduj pozycje pojazdów
    map_creator.load_vehicle_positions()
    
    # Utwórz mapę (centrum Łodzi)
    map_creator.create_map(center_lat=51.759, center_lon=19.456, zoom_start=12)
    
    # Dodaj przystanki (z klastrowaniem dla wydajności)
    print("\nDodawanie przystanków...")
    map_creator.add_stops(show_all=True, use_clustering=True)
    
    # Dodaj pojazdy
    print("\nDodawanie pojazdów...")
    map_creator.add_vehicles(use_clustering=False)  # Bez klastrowania, żeby widzieć każdy pojazd
    
    # Zapisz mapę
    print("\nZapisywanie mapy...")
    map_creator.save_map("lodz_transit_map.html")
    
    print("\n" + "=" * 60)
    print("✓ Gotowe!")
    print("=" * 60)
    print("\nOtwórz plik 'lodz_transit_map.html' w przeglądarce.")
    print("Możesz:")
    print("  - Kliknąć na przystanki aby zobaczyć szczegóły")
    print("  - Kliknąć na pojazdy aby zobaczyć informacje")
    print("  - Używać kontrolki warstw aby pokazać/ukryć elementy")
    print("  - Przybliżać i oddalać mapę")


if __name__ == "__main__":
    main()

