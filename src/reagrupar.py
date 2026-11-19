# -*- coding: utf-8 -*-
"""
Vuelve a aplicar las reglas de emparejamiento a lo que ya está cargado.

Las reglas intervienen al agrupar, de modo que mejorarlas no corrige lo agrupado antes:
«Mantequilla Colun» y «Mantequilla Calo» quedaron juntas cuando ninguna de las dos
marcas estaba en el léxico, y ahí siguen. Esto las separa sin volver a consultar los
sitios y sin perder el historial, porque los precios cuelgan de la variante y la
variante se muda entera al producto nuevo.

Hace dos pasadas, en este orden:

  1. Formato. Recalcula el formato de cada variante con la regla vigente y, si las
     variantes de un producto ya no coinciden, las separa. Hace falta porque el formato
     queda guardado en la tabla al cargar: cuando la regla empezó a reconocer lo que se
     declara contando —18 rollos, 12 huevos—, lo ya cargado siguió figurando sin
     formato. También actualiza el formato guardado del producto cuando todas sus
     variantes concuerdan.

  2. Marca. Separa los productos cuyas variantes declaran marcas reconocidas que no
     comparten ninguna.

Ninguna de las dos actúa cuando la regla se abstendría: si una variante no declara
formato, o no declara marca reconocida, el grupo se deja como está, que es lo mismo que
haría el emparejamiento.

Uso:
    python src/reagrupar.py             # muestra qué haría, sin tocar nada
    python src/reagrupar.py --aplicar   # lo hace
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import select  # noqa: E402

from emparejar import formato, marcas, normalizar  # noqa: E402
from modelo import Producto, VariantePorCadena, crear_sesion  # noqa: E402


def cargar_todo(sesion):
    """Trae productos y variantes de una vez.

    Son unos 8.000 productos y 11.000 variantes: pedirlos uno a uno a una base remota
    son miles de viajes y convierte una revisión de segundos en una de horas.
    """
    productos = {p.id: p for p in sesion.execute(select(Producto)).scalars()}
    return productos


def variantes_por_producto(sesion):
    filas = sesion.execute(
        select(VariantePorCadena.producto_id, VariantePorCadena.id,
               VariantePorCadena.nombre_en_cadena)
    ).all()
    agrupadas = defaultdict(list)
    for producto_id, variante_id, nombre in filas:
        agrupadas[producto_id].append((variante_id, nombre))
    return agrupadas


def _separar(sesion, productos, producto_id, por_clave, etiqueta, aplicar):
    """Deja el grupo mayor en el producto original y muda los demás a productos nuevos."""
    original = productos[producto_id]
    orden = sorted(
        por_clave.items(),
        key=lambda kv: (len(kv[1]),
                        any(normalizar(n) == original.nombre_normalizado
                            for _, n in kv[1])),
        reverse=True,
    )
    se_queda, se_mudan = orden[0], orden[1:]
    print(f"\n  producto {producto_id} [{original.categoria}] · por {etiqueta}")
    print(f"    se queda  {se_queda[0]}: {se_queda[1][0][1][:62]}")
    creados = 0
    for clave, variantes in se_mudan:
        print(f"    se separa {clave}: {variantes[0][1][:62]}")
        if not aplicar:
            continue
        fmt = formato(variantes[0][1])
        nuevo = Producto(
            nombre_normalizado=normalizar(variantes[0][1]),
            categoria=original.categoria,
            formato_unidad=fmt[0] if fmt else None,
            formato_cantidad=fmt[1] if fmt else None,
            variantes=original.variantes,
        )
        sesion.add(nuevo)
        sesion.flush()
        for variante_id, _ in variantes:
            sesion.get(VariantePorCadena, variante_id).producto_id = nuevo.id
        creados += 1
    return creados


def pasada_formato(sesion, productos, aplicar: bool) -> int:
    """Recalcula el formato guardado y separa los grupos que ya no concuerdan."""
    creados = 0
    actualizados = 0
    for producto_id, variantes in variantes_por_producto(sesion).items():
        por_formato = defaultdict(list)
        for variante_id, nombre in variantes:
            por_formato[formato(nombre)].append((variante_id, nombre))

        if len(por_formato) == 1:
            # Todas concuerdan: basta con dejar guardado el formato vigente.
            fmt = next(iter(por_formato))
            producto = productos[producto_id]
            unidad = fmt[0] if fmt else None
            cantidad = fmt[1] if fmt else None
            if (producto.formato_unidad != unidad
                    or (producto.formato_cantidad is None) != (cantidad is None)
                    or (cantidad is not None
                        and abs(float(producto.formato_cantidad) - cantidad) > 0.01)):
                actualizados += 1
                if aplicar:
                    producto.formato_unidad = unidad
                    producto.formato_cantidad = cantidad
            continue

        # Si alguna variante no declara formato, la regla se abstiene y no se separa.
        if None in por_formato:
            continue
        creados += _separar(sesion, productos, producto_id, por_formato, "formato", aplicar)
    print(f"\n  productos cuyo formato guardado se actualiza: {actualizados}")
    return creados


def pasada_marca(sesion, productos, aplicar: bool) -> int:
    """Separa los productos cuyas variantes declaran marcas reconocidas incompatibles."""
    creados = 0
    for producto_id, variantes in variantes_por_producto(sesion).items():
        if len(variantes) < 2:
            continue
        por_marca = defaultdict(list)
        hay_sin_marca = False
        for variante_id, nombre in variantes:
            encontradas = marcas(nombre)
            if encontradas:
                por_marca[frozenset(encontradas)].append((variante_id, nombre))
            else:
                hay_sin_marca = True
        if len(por_marca) < 2:
            continue
        claves = list(por_marca)
        if any(a & b for i, a in enumerate(claves) for b in claves[i + 1:]):
            continue
        if hay_sin_marca:
            # Con una variante sin marca la regla se abstiene; separar el resto dejaría
            # esa variante asociada a un grupo elegido al azar.
            continue
        creados += _separar(sesion, productos, producto_id,
                            {tuple(sorted(k)): v for k, v in por_marca.items()},
                            "marca", aplicar)
    return creados


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true",
                    help="escribe los cambios; sin esto solo los muestra")
    args = ap.parse_args()

    Sesion = crear_sesion()
    with Sesion() as sesion:
        productos = cargar_todo(sesion)
        print(f"{len(productos)} productos cargados\n")
        print("== Pasada 1: formato")
        por_formato = pasada_formato(sesion, productos, args.aplicar)
        if args.aplicar:
            sesion.flush()
        print(f"\n  productos nuevos por formato: {por_formato}")

        print("\n== Pasada 2: marca")
        por_marca = pasada_marca(sesion, productos, args.aplicar)
        print(f"\n  productos nuevos por marca: {por_marca}")

        if args.aplicar:
            sesion.commit()
            print(f"\nSe crearon {por_formato + por_marca} productos. "
                  f"Los precios siguen a su variante.")
        else:
            print("\nNada se escribió. Repite con --aplicar para hacerlo.")


if __name__ == "__main__":
    main()
