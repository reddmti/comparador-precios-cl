"""
API REST del comparador.

Expone lo que el front necesita: buscar un producto y ver su precio en cada cadena,
revisar el historial de un producto y calcular el costo total de una lista de compras.
No hay autenticación ni datos de usuario: la lista se asocia a un identificador de
sesión que genera el propio cliente.

Para correrla:  uvicorn api:app --reload --port 8000   (desde src/)
"""

import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cargar import emparejar_texto  # noqa: E402
from emparejar import normalizar  # noqa: E402
from modelo import Cadena, ItemLista, Lista, Precio, Producto, VariantePorCadena, crear_sesion  # noqa: E402

app = FastAPI(
    title="Comparador de precios de supermercados",
    description="Compara precios de un producto o de una lista de compras entre cadenas.",
    version="0.1.0",
)

# El front se sirve desde otro dominio (Vercel), por lo que necesita CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

Sesion = crear_sesion()


def obtener_sesion():
    with Sesion() as sesion:
        yield sesion


# ── Esquemas de respuesta ────────────────────────────────────────────────────
class PrecioCadena(BaseModel):
    cadena: str
    precio: int
    precio_por_unidad: int | None = None
    nombre_en_cadena: str
    url: str | None = None
    fecha: date


class ProductoComparado(BaseModel):
    id: int
    # Nombre para mostrar: el más corto de los que usan las cadenas. El nombre
    # normalizado no sirve para leer, porque `normalizar()` descarta «sin» junto a las
    # demás palabras de relleno y «sin lactosa» queda como «lactosa», que dice lo
    # contrario. Esa lista no se toca: cambiarla alteraría la similitud y, con ella,
    # las medidas de precisión y cobertura ya informadas.
    nombre: str
    nombre_normalizado: str
    categoria: str
    formato: str | None = None
    precios: list[PrecioCadena]
    menor_precio: int | None = None
    mayor_precio: int | None = None
    ahorro: int | None = None
    cadena_mas_barata: str | None = None


class ItemEntrada(BaseModel):
    texto: str = Field(min_length=2, max_length=120)
    cantidad: int = Field(default=1, ge=1, le=99)


class ListaEntrada(BaseModel):
    sesion_id: str = Field(min_length=8, max_length=64)
    items: list[ItemEntrada] = Field(min_length=1, max_length=100)


class TotalCadena(BaseModel):
    cadena: str
    total: int
    items_con_precio: int


class ListaComparada(BaseModel):
    lista_id: int
    # Los totales se calculan solo sobre los productos que tienen precio en todas las
    # cadenas, de modo que las cifras comparen la misma canasta y no una parcial.
    totales: list[TotalCadena]
    cadena_recomendada: str | None
    ahorro_vs_mas_cara: int
    items_comparables: int
    items_sin_comparacion: list[str]
    items_reconocidos: list[ProductoComparado]
    items_no_reconocidos: list[str]


# ── Consultas internas ───────────────────────────────────────────────────────
def precios_vigentes(sesion, producto_ids: list[int]) -> dict[int, list[PrecioCadena]]:
    """Último precio conocido de cada variante, agrupado por producto."""
    if not producto_ids:
        return {}
    ultima = (
        select(Precio.variante_id, func.max(Precio.fecha_registro).label("fecha"))
        .group_by(Precio.variante_id).subquery()
    )
    filas = sesion.execute(
        select(VariantePorCadena.producto_id, Cadena.nombre, Precio.precio,
               Precio.precio_por_unidad, VariantePorCadena.nombre_en_cadena,
               VariantePorCadena.url_producto, Precio.fecha_registro)
        .join(VariantePorCadena, VariantePorCadena.id == Precio.variante_id)
        .join(Cadena, Cadena.id == VariantePorCadena.cadena_id)
        .join(ultima, (ultima.c.variante_id == Precio.variante_id)
                      & (ultima.c.fecha == Precio.fecha_registro))
        .where(VariantePorCadena.producto_id.in_(producto_ids))
    ).all()

    agrupado: dict[int, list[PrecioCadena]] = defaultdict(list)
    for pid, cadena, precio, por_unidad, nombre, url, fecha in filas:
        agrupado[pid].append(PrecioCadena(
            cadena=cadena, precio=precio, precio_por_unidad=por_unidad,
            nombre_en_cadena=nombre, url=url, fecha=fecha))
    for lista in agrupado.values():
        lista.sort(key=lambda x: x.precio)
    return agrupado


def armar_comparacion(producto: Producto, precios: list[PrecioCadena]) -> ProductoComparado:
    formato = None
    if producto.formato_cantidad and producto.formato_unidad:
        # float() porque la base devuelve Decimal y "900.00" se ve peor que "900"
        formato = f"{float(producto.formato_cantidad):g} {producto.formato_unidad}"
    menor = min((p.precio for p in precios), default=None)
    mayor = max((p.precio for p in precios), default=None)
    # El más corto suele ser el que menos adornos de catálogo arrastra
    nombre = min((p.nombre_en_cadena for p in precios), key=len, default=None)
    return ProductoComparado(
        id=producto.id,
        nombre=nombre or producto.nombre_normalizado,
        nombre_normalizado=producto.nombre_normalizado,
        categoria=producto.categoria,
        formato=formato,
        precios=precios,
        menor_precio=menor,
        mayor_precio=mayor,
        ahorro=(mayor - menor) if menor is not None and mayor is not None else None,
        cadena_mas_barata=precios[0].cadena if precios else None,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/salud", summary="Estado del servicio y de los datos")
def salud(sesion=Depends(obtener_sesion)):
    ultima = sesion.execute(select(func.max(Precio.fecha_registro))).scalar()
    return {
        "estado": "ok",
        "productos": sesion.execute(select(func.count(Producto.id))).scalar(),
        "variantes": sesion.execute(select(func.count(VariantePorCadena.id))).scalar(),
        "precios": sesion.execute(select(func.count(Precio.id))).scalar(),
        "ultima_actualizacion": ultima,
    }


@app.get("/buscar", response_model=list[ProductoComparado],
         summary="Busca un producto y compara su precio entre cadenas")
def buscar(q: str = Query(min_length=2, max_length=80),
           limite: int = Query(default=20, ge=1, le=100),
           sesion=Depends(obtener_sesion)):
    terminos = [t for t in normalizar(q).split() if t]
    if not terminos:
        return []
    consulta = select(Producto)
    for t in terminos:
        consulta = consulta.where(Producto.nombre_normalizado.contains(t))
    productos = sesion.execute(consulta.limit(limite)).scalars().all()
    precios = precios_vigentes(sesion, [p.id for p in productos])
    comparados = [armar_comparacion(p, precios.get(p.id, [])) for p in productos]
    # Primero los que efectivamente se pueden comparar entre varias cadenas
    comparados.sort(key=lambda c: (-len(c.precios), c.menor_precio or 0))
    return comparados


@app.get("/productos/{producto_id}", response_model=ProductoComparado,
         summary="Detalle de un producto con sus precios vigentes")
def detalle(producto_id: int, sesion=Depends(obtener_sesion)):
    producto = sesion.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return armar_comparacion(producto, precios_vigentes(sesion, [producto_id]).get(producto_id, []))


@app.get("/productos/{producto_id}/historial",
         summary="Evolución del precio de un producto por cadena")
def historial(producto_id: int, dias: int = Query(default=7, ge=1, le=90),
              sesion=Depends(obtener_sesion)):
    if sesion.get(Producto, producto_id) is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    desde = date.today() - timedelta(days=dias)
    filas = sesion.execute(
        select(Cadena.nombre, Precio.fecha_registro, Precio.precio)
        .join(VariantePorCadena, VariantePorCadena.id == Precio.variante_id)
        .join(Cadena, Cadena.id == VariantePorCadena.cadena_id)
        .where(VariantePorCadena.producto_id == producto_id, Precio.fecha_registro >= desde)
        .order_by(Precio.fecha_registro)
    ).all()
    series: dict[str, list[dict]] = defaultdict(list)
    for cadena, fecha, precio in filas:
        series[cadena].append({"fecha": fecha, "precio": precio})
    return {"producto_id": producto_id, "dias": dias, "series": series}


@app.post("/listas", response_model=ListaComparada,
          summary="Compara el costo total de una lista de compras")
def comparar_lista(entrada: ListaEntrada, sesion=Depends(obtener_sesion)):
    lista = Lista(sesion_id=entrada.sesion_id)
    sesion.add(lista)
    sesion.flush()

    reconocidos: list[tuple[Producto, int]] = []
    no_reconocidos: list[str] = []
    for item in entrada.items:
        producto = emparejar_texto(sesion, item.texto)
        sesion.add(ItemLista(lista_id=lista.id, texto_original=item.texto,
                             producto_id=producto.id if producto else None,
                             cantidad=item.cantidad))
        if producto:
            reconocidos.append((producto, item.cantidad))
        else:
            no_reconocidos.append(item.texto)
    sesion.commit()

    precios = precios_vigentes(sesion, [p.id for p, _ in reconocidos])
    cadenas_activas = {c for lista_p in precios.values() for c in (x.cadena for x in lista_p)}

    # Un producto entra al total solo si tiene precio en todas las cadenas: de lo
    # contrario se compararían canastas distintas y la cadena con menos cobertura
    # aparecería como la más barata por el solo hecho de tener menos productos.
    comparables, sin_comparacion = [], []
    for producto, cantidad in reconocidos:
        disponibles = {x.cadena for x in precios.get(producto.id, [])}
        if cadenas_activas and disponibles == cadenas_activas:
            comparables.append((producto, cantidad))
        else:
            faltan = ", ".join(sorted(cadenas_activas - disponibles)) or "ninguna cadena"
            visibles = precios.get(producto.id, [])
            nombre = min((x.nombre_en_cadena for x in visibles), key=len,
                         default=producto.nombre_normalizado)
            sin_comparacion.append(f"{nombre} (sin precio en {faltan})")

    totales: dict[str, int] = defaultdict(int)
    for producto, cantidad in comparables:
        for p in precios.get(producto.id, []):
            totales[p.cadena] += p.precio * cantidad

    recomendada = min(totales, key=totales.get) if totales else None
    ahorro = (max(totales.values()) - min(totales.values())) if totales else 0

    return ListaComparada(
        lista_id=lista.id,
        totales=[TotalCadena(cadena=c, total=t, items_con_precio=len(comparables))
                 for c, t in sorted(totales.items(), key=lambda x: x[1])],
        cadena_recomendada=recomendada,
        ahorro_vs_mas_cara=ahorro,
        items_comparables=len(comparables),
        items_sin_comparacion=sin_comparacion,
        items_reconocidos=[armar_comparacion(p, precios.get(p.id, [])) for p, _ in reconocidos],
        items_no_reconocidos=no_reconocidos,
    )
