"""
Zintegrowany serwer LLM z automatycznym pobieraniem informacji o komunikacji.
Łączy scraper z serwerem LLM.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests
import json
from traffic_scraper import TrafficInfoScraper
from pathlib import Path

app = FastAPI(title="Local LLM Assistant with Traffic Info", version="1.0.0")

# Konfiguracja Ollama
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"

# Scraper
scraper = TrafficInfoScraper()
TRAFFIC_INFO_FILE = Path("traffic_info.txt")


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
    if TRAFFIC_INFO_FILE.exists():
        return TRAFFIC_INFO_FILE.read_text(encoding='utf-8')
    return "Brak aktualnych informacji o komunikacji."


def update_traffic_info() -> Dict:
    """Aktualizuje informacje o komunikacji."""
    data = scraper.scrape_all()
    scraper.save_consolidated(data, str(TRAFFIC_INFO_FILE))
    return data


def call_ollama(messages: List[Dict], model: str, temperature: float = 0.7) -> str:
    """Wywołuje model Ollama."""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Błąd połączenia z Ollama: {str(e)}")


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Local LLM Assistant with Traffic Info",
        "traffic_info_available": TRAFFIC_INFO_FILE.exists()
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint do rozmowy z LLM z automatycznym kontekstem o komunikacji miejskiej.
    """
    # Przygotuj wiadomości
    messages = []
    for msg in request.messages:
        role = msg.role
        # Popraw role jeśli jest nieprawidłowa
        if role not in ["user", "assistant", "system"]:
            role = "user"
        messages.append({"role": role, "content": msg.content})
    
    # Upewnij się, że ostatnia wiadomość ma poprawną rolę
    if messages and messages[-1]["role"] not in ["user", "assistant", "system"]:
        messages[-1]["role"] = "user"
    
    # Dodaj kontekst o komunikacji jeśli włączone
    if request.include_traffic_info:
        traffic_info = load_traffic_info()
        system_prompt = f"""Jesteś pomocnym asystentem informacyjnym dla mieszkańców Łodzi. Twoim zadaniem jest odpowiadanie na pytania o komunikację miejską w Łodzi.

WAŻNE ZASADY:
- Odpowiadaj TYLKO w języku naturalnym (polskim), NIE generuj kodu Python ani żadnego innego kodu
- Odpowiadaj krótko, konkretnie i na temat
- Używaj informacji z poniższego kontekstu
- Jeśli nie znasz odpowiedzi, powiedz to szczerze
- Odpowiadaj jak żywy człowiek, nie jak programista

PRZYKŁAD:
Pytanie: "Czy linia 5 działa?"
Odpowiedź: "Według aktualnych informacji, linia 5 ma utrudnienia w ruchu na ul. Rzgowskiej. Tramwaje są kierowane objazdem przez ulice: Rzgowska, Paderewskiego, r. Lotników Lwowskich, Pabianicka, pl. Niepodległości, Rzgowska, Dąbrowskiego. Uruchomiono również autobusową komunikację zastępczą."

Poniżej znajdują się aktualne informacje o zmianach w komunikacji, utrudnieniach i remontach:

{traffic_info}

Teraz odpowiesz na pytanie użytkownika używając powyższych informacji. Pamiętaj: odpowiadaj w języku naturalnym, NIE generuj kodu!"""
        
        # Dodaj system prompt na początku
        messages.insert(0, {
            "role": "system",
            "content": system_prompt
        })
    
    # Dodaj dodatkową instrukcję na końcu, aby upewnić się że LLM odpowiada poprawnie
    if messages and messages[-1]["role"] == "user":
        messages[-1]["content"] = messages[-1]["content"] + "\n\nOdpowiedz krótko i konkretnie w języku polskim. NIE generuj kodu!"
    
    # Wywołaj model
    response_text = call_ollama(
        messages,
        request.model,
        request.temperature
    )
    
    # Jeśli LLM zwrócił kod, spróbuj wyciągnąć tylko tekstową odpowiedź
    if "```" in response_text or "import " in response_text or "def " in response_text:
        # Wyciągnij tekst przed kodem
        lines = response_text.split('\n')
        text_lines = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if not in_code_block and not (line.strip().startswith('import ') or line.strip().startswith('def ') or line.strip().startswith('class ')):
                text_lines.append(line)
        
        if text_lines:
            response_text = '\n'.join(text_lines).strip()
        
        # Jeśli nadal jest kod, zwróć prostą odpowiedź
        if "```" in response_text or "import " in response_text:
            response_text = "Przepraszam, nie mogę wygenerować odpowiedzi w tym formacie. Spróbuj zadać pytanie inaczej."
    
    return ChatResponse(message=response_text)


@app.post("/update-traffic-info")
def update_traffic():
    """Aktualizuje informacje o komunikacji miejskiej."""
    try:
        data = update_traffic_info()
        return {
            "status": "ok",
            "changes": len(data['changes']),
            "utrudnienia": len(data['utrudnienia']),
            "remonty": len(data['remonty']),
            "total": data['total_items'],
            "scraped_at": data['scraped_at']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd aktualizacji: {str(e)}")


@app.get("/traffic-info")
def get_traffic_info():
    """Zwraca aktualne informacje o komunikacji."""
    return {
        "info": load_traffic_info(),
        "file_exists": TRAFFIC_INFO_FILE.exists()
    }


@app.get("/models")
def list_models():
    """Lista dostępnych modeli w Ollama."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        return {"models": models}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Błąd połączenia z Ollama: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    # Przy starcie aktualizuj informacje o komunikacji
    print("Aktualizowanie informacji o komunikacji...")
    try:
        update_traffic_info()
    except Exception as e:
        print(f"Ostrzeżenie: Nie udało się zaktualizować informacji: {e}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

