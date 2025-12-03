"""
Przykładowy klient do komunikacji z lokalnym LLM.
"""

import requests
from typing import List, Optional, Dict, Any


class LLMClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Wysyła wiadomość do LLM."""
        payload = {
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "temperature": temperature
        }
        
        if model:
            payload["model"] = model
        
        if functions:
            payload["functions"] = functions
        
        response = requests.post(f"{self.base_url}/chat", json=payload)
        response.raise_for_status()
        return response.json()
    
    def list_models(self) -> List[str]:
        """Zwraca listę dostępnych modeli."""
        response = requests.get(f"{self.base_url}/models")
        response.raise_for_status()
        return response.json()["models"]


# Przykład użycia
if __name__ == "__main__":
    client = LLMClient()
    
    # Przykładowa rozmowa
    messages = [
        {"role": "user", "content": "Cześć! Jak się masz?"}
    ]
    
    response = client.chat(messages)
    print("Odpowiedź:", response["message"])
    
    # Przykład z function calling
    functions = [
        {
            "name": "get_weather",
            "description": "Pobiera aktualną pogodę dla danego miasta",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Nazwa miasta"}
                },
                "required": ["city"]
            }
        }
    ]
    
    messages_with_function = [
        {"role": "user", "content": "Jaka jest pogoda w Łodzi?"}
    ]
    
    response = client.chat(messages_with_function, functions=functions)
    print("\nOdpowiedź z funkcją:", response)

