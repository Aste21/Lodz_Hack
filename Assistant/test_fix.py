#!/usr/bin/env python3
"""
Test poprawki - sprawdza czy LLM nie zwraca kodu.
"""

import requests
import json

def test_chat():
    """Test rozmowy z LLM."""
    url = "http://localhost:8000/chat"
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Czy linia 5 i 6 działa?"
            }
        ],
        "model": "llama3.1:8b",
        "temperature": 0.7,
        "include_traffic_info": True
    }
    
    print("Wysyłanie zapytania...")
    print(f"Pytanie: {payload['messages'][0]['content']}")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        answer = result.get("message", "")
        
        print("=" * 60)
        print("ODPOWIEDŹ LLM:")
        print("=" * 60)
        print(answer)
        print("=" * 60)
        print()
        
        # Sprawdź czy odpowiedź zawiera kod
        if "```" in answer or "import " in answer or "def " in answer:
            print("❌ PROBLEM: LLM zwrócił kod zamiast odpowiedzi!")
            print("   Odpowiedź zawiera elementy kodu Python")
        else:
            print("✓ OK: LLM zwrócił odpowiedź tekstową")
        
        return answer
        
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return None

if __name__ == "__main__":
    print("Test poprawki systemu LLM")
    print("=" * 60)
    print()
    test_chat()

