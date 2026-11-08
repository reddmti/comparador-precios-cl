"""
Casos reales observados en las tarjetas de producto (22-sep-2026).
Correr desde COMPARADOR DE PRECIOS/:  python -m pytest tests
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scrapers.base import precios_de_tarjeta  # noqa: E402

CASOS = [
    # Promo multi-unidad antes del precio unitario: no debe tomarse el precio por kg de la promo
    ("santa isabel, promo lleva 4",
     ["Oferta", "Lleva 4 por $3.000", "$1.875 x kg", "$1.050", "$2.625 x kg", "Lucchetti", "Spaghetti N°5 Lucchetti 400 g"],
     (1050, 2625)),
    # Oferta: el primer monto es el rebajado, el segundo el normal
    ("santa isabel, oferta", ["Oferta", "$1.000", "$1.280", "$2.500 x kg", "Talliani", "Spaghetti"], (1000, 2500)),
    ("santa isabel, simple", ["$720", "$1.800 x kg", "Coliseo", "Pasta"], (720, 1800)),
    ("unimarc, promo 4 x", ["Agregar", "Carozzi", "Pasta", "400 g", "4 x $3.000", "($1.875 x kg)", "$1.050 c/u", "($2.625 x kg)"], (1050, 2625)),
    ("unimarc, descuento %", ["Agregar", "Talliani", "Pasta", "400 g", "28%", "$1.000", "($2.500 x kg)", "$1.390", "($3.475 x kg)"], (1000, 2500)),
    ("jumbo, promo lleva 2", ["Lleva 2 por $1.950", "$2.438 x kg", "$1.340", "$3.350 x kg", "Talliani", "Spaghetti"], (1340, 3350)),
    ("pack con precio por unidad", ["$3.490", "$3.490 x un", "Carozzi", "Pack"], (3490, None)),
    ("tarjeta sin precio", ["Agotado", "Carozzi", "Pasta"], (None, None)),
    # Casos detectados el 27-sep-2026 al revisar diferencias de precio inverosímiles
    ("jumbo, promo 6 por 5", ["6 por 5 a $1.600", "$2.225 x kg", "$320", "$2.667 x kg", "Soprole", "Yogurt Batido Soprole Frutilla 120 g"], (320, 2667)),  # 320 / 0,12 kg = 2.667 por kg
    ("jumbo, precio por 100 ml pegado", ["Lleva 2 por $4.000", "$286 x 100ml", "$2.920", "$417 x 100ml", "Elite", "Jabón Líquido Elite 700 ml"], (2920, None)),
    ("jumbo, precio por 100 ml separado", ["$874 x 100 ml", "$3.913", "Pantene", "Shampoo Pantene 400 ml"], (3913, None)),
]


@pytest.mark.parametrize("lineas,esperado", [(l, e) for _, l, e in CASOS], ids=[c[0] for c in CASOS])
def test_precios_de_tarjeta(lineas, esperado):
    assert precios_de_tarjeta(lineas) == esperado
