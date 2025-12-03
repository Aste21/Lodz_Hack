"""
Backend API dla mapy i tras komunikacji miejskiej w Łodzi.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import threading
import time
import sys
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from google.transit import gtfs_realtime_pb2
import requests
import pandas as pd
import numpy as np
from pipeline.pipeline import (
    build_vehicles_trips_joined_from_feeds,
    fetch_feed,
)

# Załaduj zmienne środowiskowe
load_dotenv()

# Dodaj katalog Assistant do ścieżki
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Assistant.traffic_scraper import TrafficInfoScraper

# Importy dla tras
from routes_api.google_maps_client import get_all_routes, format_route_response
from routes_api.route_filter import filter_routes_by_disabled_lines, find_best_route

# Konfiguracja OpenAI dla taniego modelu
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY nie jest ustawiony w zmiennych środowiskowych!")

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
CHEAP_MODEL = os.getenv("OPENAI_CHEAP_MODEL", "gpt-4o")  # Tani model

VEHICLE_POSITIONS_URL = (
    "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/vehicle_positions.bin"
)
TRIP_UPDATES_URL = (
    "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/trip_updates.bin"
)

# Inicjalizuj klienta OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

app = FastAPI(title="Backend Map API", version="1.0.0")

# Scraper
scraper = TrafficInfoScraper()
# Pliki do zapisu utrudnień
UTRUDS_FILE = project_root / "mpk_utrudnienia.txt"
UTRUDS_JSON_FILE = project_root / "mpk_utrudnienia.json"


class Message(BaseModel):
    role: str
    content: str


def process_utrudnienia_with_llm(utrudnienia: List[Dict]) -> Dict:
    """Przetwarza utrudnienia przez LLM i zwraca ustrukturyzowany JSON z wyłączonymi liniami."""
    try:
        # Przygotuj tekst z utrudnieniami dla LLM
        utrudnienia_text = ""
        for i, utrudnienie in enumerate(utrudnienia, 1):
            utrudnienia_text += f"Utrudnienie {i}:\n"
            if utrudnienie.get("lines"):
                utrudnienia_text += f"  Linie: {', '.join(utrudnienie['lines'])}\n"
            if utrudnienie.get("utrudnienie"):
                utrudnienia_text += f"  Opis: {utrudnienie['utrudnienie']}\n"
            if utrudnienie.get("zmiana_sytuacji"):
                utrudnienia_text += (
                    f"  Zmiana sytuacji: {utrudnienie['zmiana_sytuacji']}\n"
                )
            utrudnienia_text += "\n"

        if not utrudnienia_text.strip():
            return {"disabled_lines": []}

        # Prompt dla LLM
        prompt = f"""Przeanalizuj poniższe utrudnienia w komunikacji miejskiej w Łodzi i zwróć JSON z listą linii które są WYŁĄCZONE Z UŻYTKU (całkowicie nie działają, nie kursują).

WAŻNE:
- Jeśli linia ma tylko opóźnienia lub objazdy, ale nadal kursuje - NIE dodawaj jej do wyłączonych
- Dodaj do wyłączonych TYLKO linie które są całkowicie wyłączone z użytku (np. "zatrzymanie ruchu", "wstrzymanie", "nie kursuje", "wyłączona")
- Jeśli w opisie jest "komunikacja została wznowiona" lub "tramwaje jadą" - linia NIE jest wyłączona
- Zawsze zwracaj uwagę na coś w rodzaju "ZMIANA SYTUACJI"

UTRUDNIENIA:
{utrudnienia_text}

Zwróć TYLKO JSON w formacie:
{{
  "disabled_lines": ["2", "5", "12", "69A"]
}}

Jeśli żadna linia nie jest wyłączona, zwróć pustą listę. Zwróć TYLKO JSON, bez dodatkowego tekstu."""

        # Wywołaj OpenAI API
        response = openai_client.chat.completions.create(
            model=CHEAP_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Jesteś asystentem który analizuje utrudnienia w komunikacji miejskiej i zwraca ustrukturyzowany JSON. Zawsze zwracaj TYLKO poprawny JSON, bez dodatkowego tekstu.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Niska temperatura dla bardziej deterministycznych odpowiedzi
        )

        response_text = response.choices[0].message.content.strip()

        # Wyciągnij JSON z odpowiedzi (może być otoczony tekstem)
        if "{" in response_text:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
            return result
        else:
            # Jeśli nie ma JSON, zwróć pusty
            return {"disabled_lines": []}

    except Exception as e:
        print(f"Błąd podczas przetwarzania utrudnień przez LLM: {e}")
        # W razie błędu zwróć pusty JSON
        return {"disabled_lines": []}


def save_utrudnienia_to_file(
    utrudnienia: List[Dict], filename: Path, structured_data: Dict = None
):
    """Zapisuje utrudnienia do pliku tekstowego."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("UTRUDNIENIA W RUCHU MPK ŁÓDŹ\n")
            f.write(f"Zaktualizowano: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            if not utrudnienia:
                f.write("Brak aktualnych utrudnień.\n")
            else:
                for i, utrudnienie in enumerate(utrudnienia, 1):
                    f.write(f"--- Utrudnienie {i} ---\n")
                    if utrudnienie.get("lines"):
                        f.write(f"Linie: {', '.join(utrudnienie['lines'])}\n")
                    if utrudnienie.get("utrudnienie"):
                        f.write(f"Utrudnienie: {utrudnienie['utrudnienie']}\n")
                    if utrudnienie.get("zmiana_sytuacji"):
                        f.write(f"Zmiana sytuacji: {utrudnienie['zmiana_sytuacji']}\n")
                    if utrudnienie.get("data_dodania"):
                        f.write(f"Data dodania: {utrudnienie['data_dodania']}\n")
                    if utrudnienie.get("source"):
                        f.write(f"Źródło: {utrudnienie['source']}\n")
                    f.write("\n")

            # Dodaj sekcję z wyłączonymi liniami jeśli są dostępne
            if structured_data:
                f.write("\n" + "=" * 80 + "\n")
                f.write("WYŁĄCZONE Z UŻYTKU (na podstawie analizy LLM):\n")
                f.write("=" * 80 + "\n\n")
                if structured_data.get("disabled_lines"):
                    f.write(
                        f"Wyłączone linie: {', '.join(structured_data['disabled_lines'])}\n"
                    )
                else:
                    f.write(
                        "Brak wyłączonych linii - wszystkie działają (mogą mieć opóźnienia lub objazdy).\n"
                    )
    except Exception as e:
        print(f"Błąd przy zapisie utrudnień do pliku: {e}")


def save_utrudnienia_json(structured_data: Dict, filename: Path):
    """Zapisuje ustrukturyzowane dane do pliku JSON."""
    try:
        if not structured_data:
            structured_data = {
                "disabled_lines": [],
            }

        data_to_save = {
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "disabled_lines": structured_data.get("disabled_lines", []),
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Błąd przy zapisie JSON: {e}")
        return False


def scraper_thread():
    """Wątek który co minutę pobiera utrudnienia MPK, przetwarza przez LLM i zapisuje do plików."""
    print("Wątek scrapera uruchomiony - pobieranie utrudnień co minutę...")

    while True:
        should_save = True  # Flaga czy zapisać pliki
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Pobieranie utrudnień MPK...")
            utrudnienia = scraper.scrape_mpk_utrudnienia()
            print(f"[{time.strftime('%H:%M:%S')}] Pobrano {len(utrudnienia)} utrudnień")

            # ZAWSZE przetwórz przez LLM aby wyciągnąć wyłączone linie (nawet jeśli brak utrudnień)
            structured_data = None
            try:
                print(
                    f"[{time.strftime('%H:%M:%S')}] Przetwarzanie przez LLM ({CHEAP_MODEL})..."
                )
                structured_data = process_utrudnienia_with_llm(utrudnienia)
                print(
                    f"[{time.strftime('%H:%M:%S')}] LLM znalazł {len(structured_data.get('disabled_lines', []))} wyłączonych linii"
                )
            except Exception as llm_error:
                print(
                    f"[{time.strftime('%H:%M:%S')}] Błąd LLM, używam pustych danych: {llm_error}"
                )
                structured_data = {
                    "disabled_lines": [],
                }

            # Zapisz pliki tylko jeśli should_save jest True
            if should_save:
                # ZAWSZE zapisz do pliku tekstowego (nawet jeśli brak utrudnień)
                save_utrudnienia_to_file(utrudnienia, UTRUDS_FILE, structured_data)
                print(f"[{time.strftime('%H:%M:%S')}] Zapisano do {UTRUDS_FILE}")

                # ZAWSZE zapisz do pliku JSON (automatycznie razem z TXT - zawsze po zapisie TXT)
                # Upewnij się że structured_data istnieje
                if not structured_data:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] structured_data jest None, ustawiam pusty dict"
                    )
                    structured_data = {
                        "disabled_lines": [],
                    }

                # Zawsze zapisz JSON (niezależnie od tego czy structured_data jest pełne czy puste)
                print(
                    f"[{time.strftime('%H:%M:%S')}] Próba zapisu JSON do {UTRUDS_JSON_FILE}..."
                )
                result = save_utrudnienia_json(structured_data, UTRUDS_JSON_FILE)
                if result:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] Zapisano JSON do {UTRUDS_JSON_FILE}"
                    )
                else:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] BŁĄD: Nie udało się zapisać JSON do {UTRUDS_JSON_FILE}"
                    )

        except (
            ConnectionError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            should_save = False
            print(
                f"[{time.strftime('%H:%M:%S')}] Błąd połączenia podczas pobierania utrudnień: {e}"
            )
            print(
                f"[{time.strftime('%H:%M:%S')}] NIE nadpisuję plików - zachowuję poprzednie dane"
            )
            # NIE zapisujemy plików przy błędzie połączenia - zachowujemy poprzednie dane

        except Exception as e:
            error_msg = str(e).lower()
            # Sprawdź czy to błąd związany z połączeniem
            if any(
                keyword in error_msg
                for keyword in [
                    "connection",
                    "connect",
                    "timeout",
                    "reset",
                    "aborted",
                    "10054",
                    "gwałtownie zamknięte",
                    "zdalnego hosta",
                ]
            ):
                should_save = False
                print(
                    f"[{time.strftime('%H:%M:%S')}] Błąd połączenia podczas pobierania utrudnień: {e}"
                )
                print(
                    f"[{time.strftime('%H:%M:%S')}] NIE nadpisuję plików - zachowuję poprzednie dane"
                )
            else:
                # Dla innych błędów też nie nadpisujemy jeśli pliki już istnieją
                if UTRUDS_FILE.exists() and UTRUDS_JSON_FILE.exists():
                    should_save = False
                    print(
                        f"[{time.strftime('%H:%M:%S')}] Błąd podczas pobierania/przetwarzania utrudnień: {e}"
                    )
                    print(
                        f"[{time.strftime('%H:%M:%S')}] NIE nadpisuję plików - zachowuję poprzednie dane"
                    )
                else:
                    # Jeśli pliki nie istnieją, zapisz puste dane żeby pliki powstały
                    print(
                        f"[{time.strftime('%H:%M:%S')}] Błąd podczas pobierania/przetwarzania utrudnień: {e}"
                    )
                    print(
                        f"[{time.strftime('%H:%M:%S')}] Pliki nie istnieją - zapisuję puste dane"
                    )
                    try:
                        empty_data = {
                            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "disabled_lines": [],
                        }
                        save_utrudnienia_json(empty_data, UTRUDS_JSON_FILE)
                        save_utrudnienia_to_file([], UTRUDS_FILE, empty_data)
                    except:
                        pass

        # Czekaj 60 sekund przed następnym pobraniem
        time.sleep(60)


@app.get("/")
def root():
    """Endpoint główny - status API."""
    return {
        "status": "ok",
        "service": "Backend Map API",
        "version": "1.0.0",
        "scraper_running": True,
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/utrudnienia")
def get_utrudnienia():
    """Zwraca aktualne utrudnienia z pliku tekstowego."""
    try:
        if UTRUDS_FILE.exists():
            content = UTRUDS_FILE.read_text(encoding="utf-8")
            return {"utrudnienia": content, "file_exists": True}
        return {"utrudnienia": "Plik nie istnieje jeszcze.", "file_exists": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd odczytu pliku: {str(e)}")


@app.get("/utrudnienia/json")
def get_utrudnienia_json():
    """Zwraca ustrukturyzowane dane o wyłączonych liniach z pliku JSON."""
    try:
        if UTRUDS_JSON_FILE.exists():
            content = UTRUDS_JSON_FILE.read_text(encoding="utf-8")
            data = json.loads(content)
            return data
        return {
            "updated_at": None,
            "disabled_lines": [],
            "file_exists": False,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Błąd odczytu pliku JSON: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    # Ustaw PYTHONPATH dla procesu uvicorn (dla reload)
    os.environ["PYTHONPATH"] = str(project_root)

    # Uruchom wątek scrapera w tle
    scraper_thread_obj = threading.Thread(target=scraper_thread, daemon=True)
    scraper_thread_obj.start()
    print("Wątek scrapera uruchomiony w tle")

    # Uruchom serwer FastAPI z automatycznym przeładowaniem przy zmianach w kodzie
    uvicorn.run(
        "backend_map:app",  # String importu - wymagany dla reload
        host="0.0.0.0",
        port=8001,  # Inny port niż integrated_server (8000)
        reload=True,  # Automatyczne przeładowanie przy zmianach
        reload_dirs=[str(project_root)],  # Obserwuj katalog główny projektu
        reload_includes=["*.py"],  # Obserwuj tylko pliki Python
    )


def fetch_gtfs_feed(url: str) -> gtfs_realtime_pb2.FeedMessage:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(resp.content)
    return feed


@app.get("/data")
def get_all_data():
    """
    Pobiera live GTFS-RT z Łodzi, przepuszcza przez pipeline
    i zwraca JEDNĄ listę rekordów (vehicles + trips połączone LEFT JOIN).
    """
    try:
        vehicle_feed = fetch_feed(VEHICLE_POSITIONS_URL)
        trip_feed    = fetch_feed(TRIP_UPDATES_URL)

        joined_df = build_vehicles_trips_joined_from_feeds(vehicle_feed, trip_feed)

        # jeden DataFrame -> jedna lista rekordów
        return joined_df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")


@app.get("/route")
def get_route(origin: str, destination: str):
    """
    Zwraca trasę komunikacją miejską z punktu A do B.
    Automatycznie filtruje trasy które używają wyłączonych linii MPK.

    Args:
        origin: Punkt startowy (adres lub współrzędne)
        destination: Punkt docelowy (adres lub współrzędne)

    Returns:
        Dict z trasą (najlepszą dostępną, bez wyłączonych linii)
    """
    try:
        # Pobierz wszystkie dostępne trasy
        all_routes = get_all_routes(origin, destination)

        if not all_routes:
            raise HTTPException(
                status_code=404, detail="Nie znaleziono tras dla podanych punktów"
            )

        # Pobierz wyłączone linie z pliku JSON
        disabled_lines = []
        if UTRUDS_JSON_FILE.exists():
            try:
                with open(UTRUDS_JSON_FILE, "r", encoding="utf-8") as f:
                    utrudnienia_data = json.load(f)
                    disabled_lines = utrudnienia_data.get("disabled_lines", [])
            except Exception as e:
                print(f"Błąd odczytu wyłączonych linii: {e}")

        # Filtruj trasy - usuń te które używają wyłączonych linii
        filtered_routes = None
        if disabled_lines:
            filtered_routes = filter_routes_by_disabled_lines(
                all_routes, disabled_lines
            )
            if not filtered_routes:
                # Jeśli wszystkie trasy używają wyłączonych linii, zwróć pierwszą z ostrzeżeniem
                return {
                    "route": format_route_response(all_routes[0]),
                    "warning": f"Wszystkie trasy używają wyłączonych linii: {', '.join(disabled_lines)}. Zwrócono najlepszą dostępną trasę.",
                    "disabled_lines": disabled_lines,
                }
            routes_to_choose = filtered_routes
        else:
            # Brak wyłączonych linii - użyj wszystkich tras
            routes_to_choose = all_routes

        # Wybierz najlepszą trasę (najkrótszą czasowo)
        best_route = find_best_route(routes_to_choose)

        if not best_route:
            raise HTTPException(status_code=500, detail="Błąd podczas wyboru trasy")

        return {
            "route": format_route_response(best_route),
            "disabled_lines": disabled_lines,
            "filtered": len(disabled_lines) > 0
            and len(filtered_routes) < len(all_routes),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Błąd podczas pobierania trasy: {str(e)}"
        )
