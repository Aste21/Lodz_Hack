# 🚀 Szybki Start

## 1. Sprawdź czy Ollama działa

```bash
ollama list
```

Powinieneś zobaczyć `llama3.1:8b`. Jeśli nie ma, pobierz:
```bash
ollama pull llama3.1:8b
```

## 2. Zainstaluj zależności (jeśli jeszcze nie)

```bash
cd Assistant
pip install -r requirements.txt
```

## 3. Pobierz aktualne informacje o komunikacji (opcjonalnie)

```bash
python traffic_scraper.py
```

Lub użyj prostszego skryptu:
```bash
python update_traffic.py
```

## 4. Uruchom serwer LLM

W jednym terminalu:
```bash
cd Assistant
python integrated_server.py
```

Serwer będzie dostępny na `http://localhost:8000`

## 5. Przetestuj system

W drugim terminalu:
```bash
cd Assistant
python test_llm.py
```

## 6. Użyj API

### Przykład z Python:

```python
import requests

response = requests.post("http://localhost:8000/chat", json={
    "messages": [
        {"role": "user", "content": "Jakie są zmiany w rozkładach jazdy?"}
    ],
    "include_traffic_info": True
})

print(response.json()["message"])
```

### Przykład z curl:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Czy są jakieś utrudnienia w ruchu?"}
    ],
    "include_traffic_info": true
  }'
```

## 7. Aktualizuj informacje o komunikacji

```bash
curl -X POST http://localhost:8000/update-traffic-info
```

## Przydatne endpointy:

- `GET /` - Status serwera
- `POST /chat` - Rozmowa z LLM
- `GET /traffic-info` - Pobierz informacje o komunikacji
- `POST /update-traffic-info` - Zaktualizuj informacje
- `GET /models` - Lista dostępnych modeli

## Przykładowe pytania:

- "Jakie są aktualne zmiany w rozkładach jazdy?"
- "Czy są jakieś utrudnienia w ruchu?"
- "Które linie tramwajowe są zmienione?"
- "Gdzie są remonty dróg?"
- "Czy linia 6 kursuje normalnie?"
- "Jakie są planowane remonty ulic?"

