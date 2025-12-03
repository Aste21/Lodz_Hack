# Vehicle Positions Monitor

System do ciągłego monitorowania pozycji pojazdów z GTFS-RT feed.

## Funkcjonalności

- 🔄 Ciągłe pobieranie danych z GTFS-RT feed co 30 sekund
- 💾 Automatyczne zapisywanie danych do bazy SQLite
- 📊 API REST do pobierania danych
- 🖨️ Wyświetlanie danych w konsoli

## Instalacja

```bash
pip install -r requirements.txt
```

## Uruchomienie

```bash
python veh_pos.py
```

Program będzie:
1. Pobierać dane co 30 sekund
2. Zapisowywać je do bazy danych `vehicle_positions.db`
3. Uruchamiać API na porcie 5000

## API Endpoints

### GET `/api/vehicle_positions`
Zwraca ostatni pobrany response z surowymi danymi i sparsowanymi pozycjami pojazdów.

**Przykład:**
```bash
curl http://127.0.0.1:5000/api/vehicle_positions
# lub z flagą -4 dla IPv4:
curl -4 http://localhost:5000/api/vehicle_positions
```

**Uwaga:** Jeśli używasz `localhost` i otrzymujesz błąd "Connection reset by peer", użyj `127.0.0.1` zamiast `localhost` lub dodaj flagę `-4` do curl, aby wymusić IPv4.

### GET `/api/vehicle_positions/db`
Zwraca ostatnie 100 pozycji z bazy danych.

**Przykład:**
```bash
curl http://127.0.0.1:5000/api/vehicle_positions/db
```

### GET `/api/health`
Health check endpoint.

**Przykład:**
```bash
curl http://127.0.0.1:5000/api/health
```

## Baza danych

Dane są zapisywane w bazie SQLite `vehicle_positions.db` w tabeli `vehicle_positions`.

## Konfiguracja

Możesz zmienić konfigurację w pliku `veh_pos.py`:
- `URL` - URL do GTFS-RT feed
- `FETCH_INTERVAL` - interwał pobierania danych (w sekundach)
- `API_PORT` - port na którym działa API

