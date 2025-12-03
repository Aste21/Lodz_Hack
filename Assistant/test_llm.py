#!/usr/bin/env python3
"""
Prosty skrypt testowy do sprawdzenia czy LLM działa.
"""

import requests
import json

def test_ollama():
    """Test połączenia z Ollama."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print("✓ Ollama działa!")
            print(f"✓ Dostępne modele: {[m['name'] for m in models]}")
            return True
        else:
            print("✗ Ollama nie odpowiada")
            return False
    except Exception as e:
        print(f"✗ Błąd połączenia z Ollama: {e}")
        print("  Upewnij się, że Ollama działa: ollama serve")
        return False

def test_server():
    """Test serwera LLM."""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✓ Serwer LLM działa!")
            print(f"  Status: {response.json()}")
            return True
        else:
            print("✗ Serwer nie odpowiada")
            return False
    except Exception as e:
        print(f"✗ Serwer nie działa: {e}")
        print("  Uruchom serwer: python integrated_server.py")
        return False

def test_chat():
    """Test rozmowy z LLM."""
    try:
        print("\n📝 Test rozmowy z LLM...")
        response = requests.post(
            "http://localhost:8000/chat",
            json={
                "messages": [
                    {"role": "user", "content": "Cześć! Jak się masz?"}
                ],
                "include_traffic_info": False  # Bez kontekstu o komunikacji na razie
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ LLM odpowiedział!")
            print(f"\nOdpowiedź: {result['message'][:200]}...")
            return True
        else:
            print(f"✗ Błąd: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"✗ Błąd: {e}")
        return False

def test_traffic_chat():
    """Test rozmowy z LLM z kontekstem o komunikacji."""
    try:
        print("\n🚌 Test rozmowy z LLM o komunikacji...")
        response = requests.post(
            "http://localhost:8000/chat",
            json={
                "messages": [
                    {"role": "user", "content": "Jakie są aktualne zmiany w rozkładach jazdy?"}
                ],
                "include_traffic_info": True
            },
            timeout=120  # Dłuższy timeout bo LLM musi przetworzyć dużo kontekstu
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ LLM odpowiedział na pytanie o komunikację!")
            print(f"\nOdpowiedź: {result['message'][:300]}...")
            return True
        else:
            print(f"✗ Błąd: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"✗ Błąd: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TEST SYSTEMU LLM")
    print("=" * 60)
    
    # Test 1: Ollama
    print("\n1. Test Ollama...")
    ollama_ok = test_ollama()
    
    if not ollama_ok:
        print("\n❌ Ollama nie działa. Uruchom: ollama serve")
        exit(1)
    
    # Test 2: Serwer
    print("\n2. Test serwera LLM...")
    server_ok = test_server()
    
    if not server_ok:
        print("\n❌ Serwer nie działa. Uruchom w osobnym terminalu:")
        print("   cd Assistant")
        print("   python integrated_server.py")
        exit(1)
    
    # Test 3: Podstawowa rozmowa
    print("\n3. Test podstawowej rozmowy...")
    chat_ok = test_chat()
    
    # Test 4: Rozmowa o komunikacji
    if chat_ok:
        print("\n4. Test rozmowy o komunikacji...")
        test_traffic_chat()
    
    print("\n" + "=" * 60)
    print("Test zakończony!")
    print("=" * 60)

