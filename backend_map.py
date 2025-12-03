"""
Backend API dla mapy i tras komunikacji miejskiej w Łodzi.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path

app = FastAPI(title="Backend Map API", version="1.0.0")


class Message(BaseModel):
    role: str
    content: str


@app.get("/")
def root():
    """Endpoint główny - status API."""
    return {
        "status": "ok",
        "service": "Backend Map API",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    import sys
    import os

    # Dodaj katalog główny projektu do PYTHONPATH przed uruchomieniem uvicorn
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Ustaw PYTHONPATH dla procesu uvicorn (dla reload)
    os.environ["PYTHONPATH"] = str(project_root)

    # Uruchom serwer z automatycznym przeładowaniem przy zmianach w kodzie
    uvicorn.run(
        "backend_map:app",  # String importu - wymagany dla reload
        host="0.0.0.0",
        port=8001,  # Inny port niż integrated_server (8000)
        reload=True,  # Automatyczne przeładowanie przy zmianach
        reload_dirs=[str(Path(__file__).parent)],  # Obserwuj katalog główny projektu
        reload_includes=["*.py"],  # Obserwuj tylko pliki Python
    )
