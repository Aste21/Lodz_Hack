# Interaktywna Mapa Komunikacji Miejskiej w Łodzi

Interaktywna mapa wyświetlająca pozycje pojazdów (autobusów i tramwajów) oraz przystanki w Łodzi.

## Instalacja

```bash
pip install -r requirements.txt
```

## Uruchomienie

```bash
python3 interactive_map.py
```

To wygeneruje plik `lodz_transit_map.html`, który możesz otworzyć w przeglądarce.

## Funkcjonalności

### Na mapie zobaczysz:

1. **Przystanki** (niebieskie markery)
   - Wszystkie przystanki komunikacji miejskiej w Łodzi
   - Kliknij na marker aby zobaczyć:
     - Nazwę przystanku
     - ID przystanku
     - Kod przystanku

2. **Pojazdy** (kolorowe markery)
   - **Czerwone ikony pociągu** - Tramwaje
   - **Zielone ikony autobusu** - Autobusy
   - **Pomarańczowe ikony** - Inne pojazdy
   - Kliknij na marker aby zobaczyć:
     - Numer linii
     - ID pojazdu
     - ID kursu
     - Status (w drodze, zatrzymany, etc.)
     - Prędkość
     - Aktualny przystanek

### Kontrolki mapy:

- **Warstwy** (w prawym górnym rogu)
  - Możesz włączać/wyłączać wyświetlanie przystanków i pojazdów
  - Możesz zmieniać styl mapy (OpenStreetMap, CartoDB, etc.)

- **Przybliżanie/oddalanie**
  - Użyj kółka myszy lub przycisków +/- na mapie

- **Legenda** (w prawym dolnym rogu)
  - Wyjaśnia znaczenie różnych markerów

## Techniczne szczegóły

- **Przystanki**: ~1206 przystanków (co drugi dla lepszej wydajności)
- **Pojazdy**: 329 pojazdów z aktualnymi pozycjami
- **Klastrowanie**: Przystanki są klastrowane dla lepszej wydajności przy oddalaniu

## Aktualizacja danych

Aby zaktualizować pozycje pojazdów:

1. Pobierz nowe pliki `.bin` z GTFS Realtime
2. Uruchom `bin_to_csv.py` aby przekonwertować je do CSV
3. Uruchom ponownie `interactive_map.py`

## Dostosowanie

Możesz zmodyfikować `interactive_map.py` aby:

- Zmienić centrum mapy
- Zmienić poziom przybliżenia
- Dodać filtrowanie po konkretnych liniach
- Dodać więcej informacji w popupach
- Zmienić kolory i ikony

## Przykład użycia w kodzie

```python
from interactive_map import LodzTransitMap

# Utwórz mapę
map_creator = LodzTransitMap()
map_creator.load_vehicle_positions()
map_creator.create_map()

# Dodaj tylko pojazdy konkretnej linii
map_creator.add_vehicles(route_filter="1")  # Tylko linia 1

# Zapisz
map_creator.save_map("moja_mapa.html")
```

