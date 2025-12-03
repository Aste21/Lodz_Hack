"""
Prosty serwer lokalnego LLM z obsługą function calling.
Używa Ollama do uruchomienia modelu lokalnie.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import ollama
import json

app = FastAPI(title="Local LLM Assistant", version="1.0.0")

# Konfiguracja Ollama
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
    """Wywołuje model Ollama używając oficjalnego klienta."""
    try:
        response = ollama.chat(
            model=model, messages=messages, options={"temperature": temperature}
        )
        if "message" not in response or "content" not in response["message"]:
            raise HTTPException(
                status_code=500,
                detail="Nieprawidłowa odpowiedź z Ollama: brak zawartości wiadomości",
            )
        return response["message"]["content"]
    except HTTPException:
        # Re-raise HTTPException bez modyfikacji
        raise
    except (ConnectionError, OSError) as e:
        # Łapiemy zarówno wbudowany ConnectionError jak i OSError (które mogą być używane przez ollama)
        raise HTTPException(
            status_code=503,
            detail=f"Nie można połączyć się z Ollama. Upewnij się, że Ollama działa: ollama serve. Błąd: {str(e)}",
        )
    except Exception as e:
        # Sprawdzamy czy to błąd połączenia z ollama (może być ollama.ConnectionError lub podobny)
        error_msg = str(e)
        error_type = type(e).__name__

        # Sprawdzamy czy to błąd połączenia (różne możliwe nazwy)
        if (
            "connection" in error_msg.lower()
            or "connect" in error_msg.lower()
            or "ConnectionError" in error_type
            or isinstance(e, (ConnectionError, OSError))
        ):
            raise HTTPException(
                status_code=503,
                detail=f"Nie można połączyć się z Ollama. Upewnij się, że Ollama działa: ollama serve. Błąd: {error_msg}",
            )

        # Sprawdzamy czy to błąd brakującego modelu
        if "model" in error_msg.lower() or "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model}' nie został znaleziony. Pobierz model: ollama pull {model}",
            )

        # Inne błędy
        raise HTTPException(
            status_code=500, detail=f"Błąd połączenia z Ollama: {error_msg}"
        )


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
        {"role": msg.role, "content": msg.content} for msg in request.messages
    ]

    # Dodaj informacje o funkcjach do system prompt jeśli są dostępne
    if request.functions:
        functions_desc = "\n".join(
            [f"- {f.name}: {f.description}" for f in request.functions]
        )
        system_msg = {
            "role": "system",
            "content": f'Dostępne funkcje:\n{functions_desc}\n\nJeśli chcesz wywołać funkcję, odpowiedz w formacie JSON: {{"function": "nazwa_funkcji", "arguments": {{...}}}}',
        }
        ollama_messages.insert(0, system_msg)

    # Wywołaj model
    response_text = call_ollama(ollama_messages, request.model, request.temperature)

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

    return ChatResponse(message=response_text, function_call=function_call)


@app.get("/models")
def list_models():
    """Lista dostępnych modeli w Ollama."""
    try:
        models_list = ollama.list()
        models = [model["name"] for model in models_list.get("models", [])]
        return {"models": models}
    except HTTPException:
        # Re-raise HTTPException bez modyfikacji
        raise
    except (ConnectionError, OSError) as e:
        # Łapiemy zarówno wbudowany ConnectionError jak i OSError
        raise HTTPException(
            status_code=503,
            detail=f"Nie można połączyć się z Ollama. Upewnij się, że Ollama działa: ollama serve. Błąd: {str(e)}",
        )
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__

        # Sprawdzamy czy to błąd połączenia
        if (
            "connection" in error_msg.lower()
            or "connect" in error_msg.lower()
            or "ConnectionError" in error_type
            or isinstance(e, (ConnectionError, OSError))
        ):
            raise HTTPException(
                status_code=503,
                detail=f"Nie można połączyć się z Ollama. Upewnij się, że Ollama działa: ollama serve. Błąd: {error_msg}",
            )

        raise HTTPException(
            status_code=500, detail=f"Błąd połączenia z Ollama: {error_msg}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
