"""
Punto de entrada para el despliegue en Vercel.

Vercel ejecuta cada archivo de esta carpeta como una función; al exponer aquí la
aplicación de FastAPI, todas las rutas se atienden desde una sola función.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import app  # noqa: E402,F401  (Vercel toma la variable `app`)
