"""
Prosty serwer lokalnego LLM z obsługą function calling.
Używa Ollama do uruchomienia modelu lokalnie.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests
import json

app = FastAPI(title="Local LLM Assistant", version="1.0.0")

# Konfiguracja Ollama
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"  # Zmień na swój model


class Message(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class Function(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = DEFAULT_MODEL
    functions: Optional[List[Function]] = None
    temperature: Optional[float] = 0.7


class ChatResponse(BaseModel):
    message: str
    function_call: Optional[Dict[str, Any]] = None


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
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Błąd połączenia z Ollama: {str(e)}")


@app.get("/")
def root():
    return {"status": "ok", "service": "Local LLM Assistant"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint do rozmowy z LLM.
    Obsługuje function calling - jeśli model zwróci funkcję, zwrócimy ją w odpowiedzi.
    """
    # Konwersja wiadomości do formatu Ollama
    ollama_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in request.messages
    ]
    
    # Dodaj informacje o funkcjach do system prompt jeśli są dostępne
    if request.functions:
        functions_desc = "\n".join([
            f"- {f.name}: {f.description}"
            for f in request.functions
        ])
        system_msg = {
            "role": "system",
            "content": f"Dostępne funkcje:\n{functions_desc}\n\nJeśli chcesz wywołać funkcję, odpowiedz w formacie JSON: {{\"function\": \"nazwa_funkcji\", \"arguments\": {{...}}}}"
        }
        ollama_messages.insert(0, system_msg)
    
    # Wywołaj model
    response_text = call_ollama(
        ollama_messages,
        request.model,
        request.temperature
    )
    
    # Próbuj wyciągnąć function call z odpowiedzi
    function_call = None
    try:
        # Szukaj JSON w odpowiedzi
        if "{" in response_text and "function" in response_text:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            parsed = json.loads(json_str)
            if "function" in parsed:
                function_call = parsed
    except:
        pass
    
    return ChatResponse(
        message=response_text,
        function_call=function_call
    )


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
    uvicorn.run(app, host="0.0.0.0", port=8000)

