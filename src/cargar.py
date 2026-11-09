"""
Carga de productos obtenidos a la base de datos.

Es el paso que une la extracción con la consulta: toma los productos que entrega el
scraper, los agrupa en productos equivalentes con el mismo criterio evaluado en el
informe (formato, variantes, números, marca y similitud sobre el umbral) y registra el precio
del día. Si un producto ya existe, se le agrega la variante de la cadena; si el precio
del día ya fue registrado, se actualiza en lugar de duplicarse.

Uso:
    python src/cargar.py datos.json            # carga un archivo ya obtenido
    python src/cargar.py --extraer arroz leche # obtiene y carga en un paso
"""

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emparejar import (  # noqa: E402
    formato, marcas_compatibles, normalizar, numeros, similitud, variantes,
)
from modelo import Cadena, ItemLista, Precio, Producto, VariantePorCadena, crear_sesion  # noqa: E402

UMBRAL = 80  # el seleccionado en la evaluación: 96,0% de precisión y 81,4% de cobertura


def clave_variantes(nombre: str) -> str:
    return "|".join(sorted(variantes(nombre)))


def buscar_producto(sesion, nombre: str, cadena_id: int) -> Producto | None:
    """
    Producto ya registrado que sea equivalente a este nombre, si existe.

    La búsqueda no se restringe a la categoría: un mismo producto puede aparecer en
    más de una consulta (unos fideos de arroz salen tanto en «arroz» como en «fideos»)
    y debe quedar registrado una sola vez.

    Se descartan los productos que ya tienen una variante de esta misma cadena: dos
    artículos distintos de una tienda no son el mismo producto, aunque sus nombres se
    parezcan. Sin esta regla, «Corbatas Lucchetti» y «Canutos Lucchetti» de la misma
    tienda terminaban agrupados por compartir la marca y el formato.
    """
    fmt = formato(nombre)
    unidad, cantidad = (fmt if fmt else (None, None))
    candidatos = sesion.query(Producto).filter(
        Producto.formato_unidad == unidad,
        Producto.formato_cantidad == cantidad,
        Producto.variantes == clave_variantes(nombre),
    ).all()
    nums = numeros(nombre)
    mejor, mejor_score = None, UMBRAL - 0.01
    objetivo = normalizar(nombre)
    for c in candidatos:
        if numeros(c.nombre_normalizado) != nums:
            continue
        # Marcas distintas, productos distintos: «Leche Soprole Sin Lactosa Entera» y
        # «Leche entera surlat sin lactosa» comparten formato, variantes y 87 de
        # similitud, y no son el mismo producto.
        if not marcas_compatibles(nombre, c.nombre_normalizado):
            continue
        s = similitud(nombre, c.nombre_normalizado)
        # Un producto que ya tiene variante de esta cadena solo se reutiliza si el
        # nombre normalizado es idéntico, es decir, cuando la tienda publica el mismo
        # artículo con dos redacciones. Si solo se parece, es otro producto.
        # La consulta va directo a la base: la colección en memoria del producto puede
        # no incluir las variantes agregadas en esta misma carga.
        ya_en_la_cadena = sesion.query(VariantePorCadena.id).filter_by(
            producto_id=c.id, cadena_id=cadena_id).first() is not None
        if ya_en_la_cadena and c.nombre_normalizado != objetivo:
            continue
        if s > mejor_score:
            mejor, mejor_score = c, s
    return mejor


def cargar_productos(sesion, productos: list[dict], fecha: date | None = None) -> dict:
    """Registra una obtención completa. Devuelve el recuento de lo que hizo."""
    fecha = fecha or date.today()
    cadenas = {c.nombre: c for c in sesion.query(Cadena).all()}
    resumen = {"productos_nuevos": 0, "variantes_nuevas": 0, "precios": 0, "omitidos": 0}

    for p in productos:
        nombre, precio = p.get("nombre"), p.get("precio")
        cadena = cadenas.get(p.get("tienda"))
        if not (nombre and precio and cadena):
            resumen["omitidos"] += 1
            continue
        categoria = p.get("consulta", "sin categoría")

        # Si esta cadena ya publicó este mismo nombre, se reutiliza su variante: ocurre
        # cuando un producto aparece bajo más de una consulta.
        variante = sesion.query(VariantePorCadena).filter_by(
            cadena_id=cadena.id, nombre_en_cadena=nombre).one_or_none()
        producto = variante.producto if variante else buscar_producto(sesion, nombre, cadena.id)

        if producto is None:
            fmt = formato(nombre)
            producto = Producto(
                nombre_normalizado=normalizar(nombre),
                categoria=categoria,
                formato_unidad=fmt[0] if fmt else None,
                formato_cantidad=fmt[1] if fmt else None,
                variantes=clave_variantes(nombre),
            )
            sesion.add(producto)
            sesion.flush()
            resumen["productos_nuevos"] += 1

        if variante is None:
            variante = VariantePorCadena(
                producto_id=producto.id, cadena_id=cadena.id, nombre_en_cadena=nombre,
                url_producto=p.get("url"),
                score=similitud(nombre, producto.nombre_normalizado),
            )
            sesion.add(variante)
            sesion.flush()
            resumen["variantes_nuevas"] += 1

        registro = sesion.query(Precio).filter_by(
            variante_id=variante.id, fecha_registro=fecha).one_or_none()
        if registro is None:
            sesion.add(Precio(
                variante_id=variante.id, precio=int(precio),
                precio_por_unidad=int(p["precio_por_kg"]) if p.get("precio_por_kg") else None,
                fecha_registro=fecha,
            ))
            resumen["precios"] += 1
        else:
            registro.precio = int(precio)
            if p.get("precio_por_kg"):
                registro.precio_por_unidad = int(p["precio_por_kg"])

    sesion.commit()
    return resumen


# El texto que escribe una persona es más pobre que el nombre publicado por la tienda:
# «leche soprole entera 1 l» contra «Leche Soprole Entera Natural 1 L» da 83 de
# similitud, porque la palabra que falta cuesta puntos. Este umbral estuvo en 88 para
# no emparejar marcas distintas, y con eso solo 3 de 15 listas realistas encontraban su
# producto. La cuarta regla de rechazo, la de marca, se hace cargo de ese riesgo de
# forma directa, así que el umbral vuelve al 80 que seleccionó la evaluación.
UMBRAL_TEXTO_LIBRE = 80


def emparejar_texto(sesion, texto: str) -> Producto | None:
    """
    Producto que corresponde a un texto escrito por el usuario en su lista.

    Se aplican las mismas reglas de rechazo que en la carga: si el texto declara un
    formato, debe coincidir; y las variantes y los números deben ser iguales. Sin esas
    reglas, «detergente omo líquido 3 l» se empareja con un detergente de otra marca.
    """
    objetivo = normalizar(texto)
    if not objetivo:
        return None
    fmt, vars_txt, nums_txt = formato(texto), variantes(texto), numeros(texto)

    consulta = sesion.query(Producto)
    if fmt:
        consulta = consulta.filter(Producto.formato_unidad == fmt[0],
                                   Producto.formato_cantidad == fmt[1])
    mejor, mejor_score = None, UMBRAL_TEXTO_LIBRE - 0.01
    for producto in consulta.all():
        if variantes(producto.nombre_normalizado) != vars_txt:
            continue
        # Los números del texto deben estar en el producto, pero no al revés: quien
        # escribe «spaghetti lucchetti» acepta el «N°5», mientras que quien escribe
        # «spaghetti n°3» no debe recibir el N°5.
        if not nums_txt <= numeros(producto.nombre_normalizado):
            continue
        if not marcas_compatibles(objetivo, producto.nombre_normalizado):
            continue
        s = similitud(objetivo, producto.nombre_normalizado)
        if s > mejor_score:
            mejor, mejor_score = producto, s
    return mejor


async def _extraer(consultas: list[str]) -> list[dict]:
    from engine import scrape_todos
    salida = []
    for consulta in consultas:
        productos = await scrape_todos(consulta)
        for p in productos:
            d = p.to_dict()
            d["consulta"] = consulta
            salida.append(d)
        print(f"  '{consulta}': {len(productos)} productos", flush=True)
    return salida


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga productos a la base de datos")
    parser.add_argument("archivo", nargs="?", help="JSON con los productos obtenidos")
    parser.add_argument("--extraer", nargs="+", metavar="CONSULTA",
                        help="obtiene las consultas indicadas y las carga")
    args = parser.parse_args()

    if args.extraer:
        productos = asyncio.run(_extraer(args.extraer))
    elif args.archivo:
        datos = json.loads(Path(args.archivo).read_text(encoding="utf8"))
        productos = datos["productos"] if isinstance(datos, dict) else datos
    else:
        parser.error("indica un archivo o usa --extraer")

    Sesion = crear_sesion()
    with Sesion() as sesion:
        resumen = cargar_productos(sesion, productos)
    print(f"Cargados {len(productos)} registros: {resumen}")


if __name__ == "__main__":
    main()
