"""
Casos de normalización y emparejamiento tomados de productos reales de las tres
cadenas (conjunto del 27-sep-2026). Correr desde COMPARADOR DE PRECIOS/: python -m pytest
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from emparejar import formato, normalizar, numeros, similitud, variantes  # noqa: E402


@pytest.mark.parametrize("nombre,esperado", [
    ("Leche Colun Entera 1 L", ("ml", 1000.0)),
    ("Aceite miraflores maravilla botella 900 cc", ("ml", 900.0)),
    ("Arroz Grado 1 Tucapel 1 kg", ("g", 1000.0)),
    ("Spaghetti N°5 Lucchetti 400 g", ("g", 400.0)),
    ("Detergente líquido ariel 1.8 l", ("ml", 1800.0)),
    ("Papel Higiénico Elite Doble Hoja 4 un.", None),  # el nombre no declara formato
    # En Chile el punto separa miles y la coma es decimal
    ("Leche en polvo nido entera tarro 1.350 g", ("g", 1350.0)),
    ("Aceite de oliva 1,5 L", ("ml", 1500.0)),
    # El pack se mide por su contenido total, para no confundirlo con la unidad suelta
    ("Pack 12 un. Leche Soprole Semidescremada Natural 1 L", ("ml", 12000.0)),
    ("Galleta salada club social 9 un de 24 g", ("g", 216.0)),
    # Las 100 bolsitas van dentro de la caja de 200 g: no se multiplica
    ("Té Ceylán Teefix 100 un. Caja 200 g", ("g", 200.0)),
])
def test_formato_se_lleva_a_unidad_base(nombre, esperado):
    assert formato(nombre) == esperado


def test_normalizar_quita_relleno_formato_y_repeticiones():
    assert normalizar("Colun Leche entera colun sin tapa 1 l") == "colun leche entera tapa"


def test_normalizar_conserva_los_numeros_de_un_digito():
    # Distinguen "grado 1" de "grado 2" y "n°3" de "n°5"
    assert "1" in normalizar("Arroz Grado 1 Tucapel 1 kg").split()
    assert "5" in normalizar("Spaghetti N°5 Lucchetti 400 g").split()


@pytest.mark.parametrize("a,b", [
    ("Aceite de Maravilla Miraflores 900 ml", "Aceite miraflores maravilla botella 900 cc"),
    ("Spaghetti N°5 Lucchetti 400 g", "Pasta spaghetti n° 5 lucchetti 400 g"),
])
def test_pares_equivalentes_superan_el_umbral(a, b):
    assert similitud(a, b) >= 85
    assert formato(a) == formato(b)
    assert variantes(a) == variantes(b)
    assert numeros(a) == numeros(b)


def test_variantes_distinguen_productos_parecidos():
    a, b = "Leche Surlat Entera 1 L", "Leche Surlat Entera Sin Lactosa 1 L"
    assert similitud(a, b) >= 80          # el texto casi no los separa
    assert variantes(a) != variantes(b)   # la regla sí


def test_numeros_distinguen_productos_parecidos():
    a, b = "Pasta Spaghetti N°3 Carozzi 400 g", "Pasta Spaghetti N°5 Carozzi 400 g"
    assert similitud(a, b) >= 90          # el texto casi no los separa
    assert numeros(a) != numeros(b)       # la regla sí
