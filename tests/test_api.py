"""
Pruebas de la carga y de la API sobre una base en memoria.

No tocan la red ni la base real: se construye un conjunto pequeño de productos con los
casos que importan (el mismo producto en tres cadenas, un producto presente en una sola,
y dos artículos distintos de una misma tienda con nombres parecidos).
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import api as api_modulo  # noqa: E402
from cargar import cargar_productos, emparejar_texto  # noqa: E402
from modelo import Producto, VariantePorCadena, crear_sesion  # noqa: E402

PRODUCTOS = [
    # El mismo aceite en las tres cadenas, con nombres distintos
    {"nombre": "Aceite de Maravilla Miraflores 900 ml", "precio": 2390, "precio_por_kg": 2656,
     "tienda": "Jumbo", "consulta": "aceite", "url": "https://jumbo.cl/a"},
    {"nombre": "Aceite de Maravilla Miraflores 900 ml", "precio": 2090, "precio_por_kg": 2322,
     "tienda": "Santa Isabel", "consulta": "aceite", "url": "https://santaisabel.cl/a"},
    {"nombre": "Aceite miraflores maravilla botella 900 cc", "precio": 3090, "precio_por_kg": 3433,
     "tienda": "Unimarc", "consulta": "aceite", "url": "https://unimarc.cl/a"},
    # Solo en una cadena: no debe entrar al total comparable
    {"nombre": "Aceite de Oliva Huasco Extra Virgen 1 L", "precio": 8990, "precio_por_kg": 8990,
     "tienda": "Jumbo", "consulta": "aceite", "url": "https://jumbo.cl/b"},
    # Dos artículos distintos de la misma tienda con nombres parecidos
    {"nombre": "Corbatas Lucchetti 400 g", "precio": 1090, "precio_por_kg": 2725,
     "tienda": "Jumbo", "consulta": "fideos", "url": "https://jumbo.cl/c"},
    {"nombre": "Canutos Lucchetti 400 g", "precio": 1150, "precio_por_kg": 2875,
     "tienda": "Jumbo", "consulta": "fideos", "url": "https://jumbo.cl/d"},
]


@pytest.fixture()
def sesion(tmp_path):
    # Archivo temporal en vez de ":memory:": SQLite crea una base distinta por
    # conexión en memoria, y la API abre una conexión propia por consulta.
    Sesion = crear_sesion(f"sqlite:///{tmp_path.as_posix()}/prueba.db")
    with Sesion() as s:
        cargar_productos(s, PRODUCTOS)
        yield s


def test_el_mismo_producto_de_tres_cadenas_queda_en_un_solo_registro(sesion):
    producto = sesion.query(Producto).filter(
        Producto.nombre_normalizado.contains("miraflores")).one()
    cadenas = {v.cadena.nombre for v in producto.variantes_cadena}
    assert cadenas == {"Jumbo", "Santa Isabel", "Unimarc"}


def test_dos_articulos_distintos_de_una_tienda_no_se_agrupan(sesion):
    corbatas = sesion.query(VariantePorCadena).filter_by(
        nombre_en_cadena="Corbatas Lucchetti 400 g").one()
    canutos = sesion.query(VariantePorCadena).filter_by(
        nombre_en_cadena="Canutos Lucchetti 400 g").one()
    assert corbatas.producto_id != canutos.producto_id


def test_cargar_dos_veces_no_duplica_precios(sesion):
    antes = sesion.query(Producto).count()
    cargar_productos(sesion, PRODUCTOS)
    assert sesion.query(Producto).count() == antes


def test_emparejar_texto_respeta_la_marca(sesion):
    assert emparejar_texto(sesion, "aceite maravilla miraflores 900 ml") is not None
    # Otra marca con el mismo formato no debe emparejarse
    assert emparejar_texto(sesion, "aceite maravilla chef 900 ml") is None


@pytest.fixture()
def cliente(monkeypatch, tmp_path):
    Sesion = crear_sesion(f"sqlite:///{tmp_path.as_posix()}/api.db")
    with Sesion() as s:
        cargar_productos(s, PRODUCTOS)
    monkeypatch.setattr(api_modulo, "Sesion", Sesion)
    return TestClient(api_modulo.app)


def test_buscar_devuelve_los_precios_de_cada_cadena(cliente):
    r = cliente.get("/buscar", params={"q": "aceite maravilla miraflores"})
    assert r.status_code == 200
    producto = r.json()[0]
    assert len(producto["precios"]) == 3
    assert producto["cadena_mas_barata"] == "Santa Isabel"
    assert producto["ahorro"] == 1000  # 3.090 - 2.090


def test_lista_compara_solo_lo_que_existe_en_todas_las_cadenas(cliente):
    r = cliente.post("/listas", json={"sesion_id": "prueba-0001", "items": [
        {"texto": "aceite de maravilla miraflores 900 ml", "cantidad": 2},
        {"texto": "aceite de oliva huasco extra virgen 1 l", "cantidad": 1},
        {"texto": "producto inexistente zzz", "cantidad": 1},
    ]})
    datos = r.json()
    assert datos["items_comparables"] == 1           # solo el que está en las tres
    assert len(datos["items_sin_comparacion"]) == 1  # el de una sola cadena
    assert datos["items_no_reconocidos"] == ["producto inexistente zzz"]
    assert datos["cadena_recomendada"] == "Santa Isabel"
    assert datos["ahorro_vs_mas_cara"] == 2000       # (3.090 - 2.090) x 2 unidades


def test_producto_inexistente_responde_404(cliente):
    assert cliente.get("/productos/999999").status_code == 404
