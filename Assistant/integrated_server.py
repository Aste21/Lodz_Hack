"""
Zintegrowany serwer LLM z automatycznym pobieraniem informacji o komunikacji.
Używa OpenAI API (GPT-5.1).
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from openai import OpenAI
import os
import re
from dotenv import load_dotenv
from traffic_scraper import TrafficInfoScraper
from pathlib import Path

# Załaduj zmienne środowiskowe
load_dotenv()

app = FastAPI(title="OpenAI Assistant with Traffic Info", version="2.0.0")

# Konfiguracja OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY nie jest ustawiony w zmiennych środowiskowych!")

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.1")

# Inicjalizuj klienta OpenAI
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

# Scraper
scraper = TrafficInfoScraper()
# Ścieżka do pliku w katalogu głównym projektu (jeden poziom wyżej od Assistant/)
TRAFFIC_INFO_FILE = Path(__file__).parent.parent / "traffic_info.txt"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = DEFAULT_MODEL
    temperature: Optional[float] = 0.7
    include_traffic_info: Optional[bool] = True


class ChatResponse(BaseModel):
    message: str


def load_traffic_info() -> str:
    """Ładuje informacje o komunikacji z pliku."""
    try:
        if TRAFFIC_INFO_FILE.exists():
            content = TRAFFIC_INFO_FILE.read_text(encoding="utf-8")
            if content.strip():
                return content
            return "Plik traffic_info.txt istnieje, ale jest pusty. Uruchom aktualizację: POST /update-traffic-info"
        return "Brak aktualnych informacji o komunikacji. Plik traffic_info.txt nie istnieje. Uruchom aktualizację: POST /update-traffic-info"
    except Exception as e:
        return f"Błąd przy ładowaniu informacji o komunikacji: {str(e)}"


def extract_sources(traffic_info: str) -> List[str]:
    """Wyciąga wszystkie źródła (linki) z traffic_info.txt."""
    sources = []
    # Szukaj linii z "Źródło: https://"
    pattern = r"Źródło:\s*(https?://[^\s\n]+)"
    matches = re.findall(pattern, traffic_info)
    sources.extend(matches)
    # Usuń duplikaty zachowując kolejność
    seen = set()
    unique_sources = []
    for source in sources:
        if source not in seen:
            seen.add(source)
            unique_sources.append(source)
    return unique_sources


def update_traffic_info() -> Dict:
    """Aktualizuje informacje o komunikacji."""
    data = scraper.scrape_all()
    scraper.save_consolidated(data, str(TRAFFIC_INFO_FILE))
    return data


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "OpenAI Assistant with Traffic Info",
        "model": DEFAULT_MODEL,
        "traffic_info_available": TRAFFIC_INFO_FILE.exists(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint do rozmowy z OpenAI z automatycznym kontekstem o komunikacji miejskiej.
    """
    # Przygotuj wiadomości
    messages = []
    for msg in request.messages:
        role = msg.role
        if role not in ["user", "assistant", "system"]:
            role = "user"
        messages.append({"role": role, "content": msg.content})

    # Dodaj kontekst o komunikacji jeśli włączone
    sources = []
    if request.include_traffic_info:
        traffic_info = load_traffic_info()
        # Wyciągnij źródła
        sources = extract_sources(traffic_info)

        system_prompt = f"""Jesteś pomocnym asystentem informacyjnym dla mieszkańców Łodzi. Odpowiadasz na pytania o komunikację miejską w Łodzi.

WAŻNE ZASADY:
1. Odpowiadaj TYLKO w języku naturalnym (polskim), NIE generuj kodu ani JSON
2. Odpowiadaj krótko, konkretnie i na temat
3. Używaj TYLKO informacji z poniższego kontekstu
4. Jeśli linia/ulica jest wymieniona w kontekście (np. "Linie: 2, 3, 6"), oznacza to że ma utrudnienia lub zmiany
5. Jeśli linia/ulica NIE jest wymieniona w kontekście, oznacza to że działa normalnie
6. ZAWSZE na końcu odpowiedzi podaj źródła (linki) z których pochodzą informacje, które użyłeś
7. NIGDY nie zwracaj JSON - tylko tekstową odpowiedź

AKTUALNE INFORMACJE O KOMUNIKACJI W ŁODZI:
{traffic_info}

TERAZ: Odpowiedz na pytanie użytkownika używając POWYŻSZYCH informacji. Jeśli linia/ulica jest wymieniona w informacjach, oznacza to że ma utrudnienia lub zmiany. Jeśli nie jest wymieniona, działa normalnie. Na końcu odpowiedzi ZAWSZE dodaj sekcję "Źródła:" z linkami do stron z których pochodzą informacje. Odpowiadaj w języku naturalnym, NIE generuj kodu ani JSON!"""

        messages.insert(0, {"role": "system", "content": system_prompt})

    # Wywołaj OpenAI API
    try:
        response = client.chat.completions.create(
            model=request.model or DEFAULT_MODEL,
            messages=messages,
            temperature=request.temperature,
        )

        response_text = response.choices[0].message.content

        if not response_text:
            raise HTTPException(status_code=500, detail="Brak odpowiedzi z OpenAI API")

        # Dodaj źródła na końcu jeśli są dostępne i nie zostały już dodane przez model
        if request.include_traffic_info and sources:
            # Sprawdź czy model już dodał źródła
            if "Źródło" not in response_text and "Źródła" not in response_text:
                sources_text = "\n\nŹródła:\n" + "\n".join(
                    f"- {source}" for source in sources[:10]
                )  # Max 10 źródeł
                response_text += sources_text
            # Jeśli model dodał źródła, ale są niepełne, dodaj pozostałe
            elif len(sources) > 0:
                # Sprawdź które źródła już są w odpowiedzi
                existing_sources = [s for s in sources if s in response_text]
                missing_sources = [s for s in sources if s not in existing_sources]
                if missing_sources:
                    additional_sources = "\n" + "\n".join(
                        f"- {source}" for source in missing_sources[:5]
                    )
                    response_text += additional_sources

        return ChatResponse(message=response_text)

    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            raise HTTPException(
                status_code=401,
                detail="Błąd autoryzacji OpenAI API. Sprawdź OPENAI_API_KEY w .env",
            )
        elif "rate_limit" in error_msg.lower():
            raise HTTPException(
                status_code=429, detail="Przekroczono limit zapytań do OpenAI API"
            )
        else:
            raise HTTPException(
                status_code=500, detail=f"Błąd połączenia z OpenAI API: {error_msg}"
            )


@app.post("/update-traffic-info")
def update_traffic():
    """Aktualizuje informacje o komunikacji miejskiej."""
    try:
        data = update_traffic_info()
        return {
            "status": "ok",
            "changes": len(data["changes"]),
            "utrudnienia": len(data["utrudnienia"]),
            "remonty": len(data["remonty"]),
            "total": data["total_items"],
            "scraped_at": data["scraped_at"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd aktualizacji: {str(e)}")


@app.get("/traffic-info")
def get_traffic_info():
    """Zwraca aktualne informacje o komunikacji."""
    return {"info": load_traffic_info(), "file_exists": TRAFFIC_INFO_FILE.exists()}


if __name__ == "__main__":
    import uvicorn
    import sys
    import os

    # Dodaj katalog główny projektu do PYTHONPATH przed uruchomieniem uvicorn
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Ustaw PYTHONPATH dla procesu uvicorn (dla reload)
    os.environ["PYTHONPATH"] = str(project_root)

    # Przy starcie aktualizuj informacje o komunikacji
    print("Aktualizowanie informacji o komunikacji...")
    try:
        update_traffic_info()
    except Exception as e:
        print(f"Ostrzeżenie: Nie udało się zaktualizować informacji: {e}")

    # Uruchom serwer z automatycznym przeładowaniem przy zmianach w kodzie
    uvicorn.run(
        "Assistant.integrated_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)],
        reload_includes=["*.py"],
    )
