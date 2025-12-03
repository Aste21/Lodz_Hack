# Local LLM Assistant

Prosty serwer lokalnego LLM z automatycznym pobieraniem informacji o komunikacji miejskiej w Łodzi.

## Funkcje

- ✅ Lokalny LLM przez Ollama
- ✅ Automatyczne scrapowanie informacji o komunikacji z:
  - MPK Łódź - zmiany rozkładów jazdy
  - MPK Łódź - utrudnienia w ruchu
  - lodz.pl - remonty i zamknięcia dróg
- ✅ Konsolidacja danych w jeden dokument dla LLM
- ✅ Automatyczne dodawanie kontekstu o komunikacji do rozmów

## Wymagania

1. **Ollama** - zainstaluj z https://ollama.ai
2. Pobierz model: `ollama pull llama3.1:8b` (lub inny model)

## Instalacja

```bash
pip install -r requirements.txt
```

## Uruchomienie

### Podstawowy serwer (bez scrapowania):
```bash
python llm_server.py
```

### Zintegrowany serwer (z automatycznym scrapowaniem):
```bash
python integrated_server.py
```

Serwer będzie dostępny na `http://localhost:8000`

**Uwaga:** Przy pierwszym uruchomieniu `integrated_server.py` automatycznie pobierze informacje o komunikacji.

## Użycie

### Przykład z klientem Python:

```python
import requests

# Podstawowa rozmowa
response = requests.post("http://localhost:8000/chat", json={
    "messages": [
        {"role": "user", "content": "Jakie są zmiany w rozkładach jazdy?"}
    ],
    "include_traffic_info": True  # Automatycznie doda kontekst o komunikacji
})

print(response.json()["message"])
```

### Aktualizacja informacji o komunikacji:

```bash
curl -X POST http://localhost:8000/update-traffic-info
```

### Pobranie informacji o komunikacji:

```bash
curl http://localhost:8000/traffic-info
```

### Uruchomienie scrapera osobno:

```bash
python traffic_scraper.py
```

To stworzy pliki:
- `traffic_info.txt` - skonsolidowany tekst dla LLM
- `traffic_info.json` - surowe dane w JSON

## API Endpoints

### Podstawowy serwer (`llm_server.py`):
- `GET /` - Status serwera
- `POST /chat` - Rozmowa z LLM
- `GET /models` - Lista dostępnych modeli

### Zintegrowany serwer (`integrated_server.py`):
- `GET /` - Status serwera
- `POST /chat` - Rozmowa z LLM (z automatycznym kontekstem o komunikacji)
- `POST /update-traffic-info` - Aktualizuje informacje o komunikacji
- `GET /traffic-info` - Zwraca aktualne informacje o komunikacji
- `GET /models` - Lista dostępnych modeli

## Przykłady pytań do LLM

Po uruchomieniu zintegrowanego serwera możesz pytać:

- "Jakie są aktualne zmiany w rozkładach jazdy?"
- "Czy są jakieś utrudnienia w ruchu?"
- "Które linie tramwajowe są zmienione?"
- "Gdzie są remonty dróg?"
- "Czy linia 6 kursuje normalnie?"

LLM będzie miał dostęp do aktualnych informacji ze wszystkich źródeł!

