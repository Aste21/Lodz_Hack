# Alerts & Vehicle Positions Monitor

System do ciągłego monitorowania alertów i vehicle_positions z GTFS-RT feed.

## Funkcjonalności

- 🔄 Ciągłe pobieranie alertów z GTFS-RT feed co 10 sekund
- 🔄 Ciągłe pobieranie vehicle_positions z GTFS-RT feed co 10 sekund
- 💾 Automatyczne zapisywanie alertów do plików binarnych gdy są wykryte
- 💾 Automatyczne zapisywanie vehicle_positions do plików binarnych gdy zawierają encje z trip_update
- 📊 Wyświetlanie informacji o znalezionych alertach i trip_updates

## Instalacja

```bash
pip install -r requirements.txt
```

## Uruchomienie

```bash
python alerts_monitor.py
```

Program będzie:
1. Pobierać alerty co 10 sekund
2. Sprawdzać czy są jakieś alerty - jeśli tak, zapisywać do `saved_alerts/`
3. Pobierać vehicle_positions co 10 sekund
4. Sprawdzać czy są encje z trip_update - jeśli tak, zapisywać do `saved_vehicle_positions/`
5. Wyświetlać informacje o znalezionych alertach i trip_updates

## Struktura plików

- **Alerty** są zapisywane w folderze `saved_alerts/` w formacie:
  - `alerts_YYYYMMDD_HHMMSS.bin` - pliki binarne z alertami

- **Vehicle Positions** są zapisywane w folderze `saved_vehicle_positions/` w formacie:
  - `vehicle_positions_YYYYMMDD_HHMMSS.bin` - pliki binarne z vehicle_positions zawierające encje z trip_update

## Konfiguracja

Możesz zmienić konfigurację w pliku `alerts_monitor.py`:
- `ALERTS_URL` - URL do GTFS-RT feed z alertami
- `VEHICLE_POSITIONS_URL` - URL do GTFS-RT feed z vehicle_positions
- `FETCH_INTERVAL` - interwał pobierania danych (w sekundach, domyślnie 10)
- `ALERTS_DIR` - folder na zapisane alerty
- `VEHICLE_POSITIONS_DIR` - folder na zapisane vehicle_positions

