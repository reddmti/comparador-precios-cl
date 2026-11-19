# -*- coding: utf-8 -*-
"""
Separa los productos cuyas variantes resultan ser de marcas distintas.

El léxico de marcas solo interviene al agrupar, de modo que ampliarlo no corrige lo ya
agrupado: «Mantequilla Colun» y «Mantequilla Calo» quedaron juntas cuando ninguna de
las dos marcas estaba en la lista, y ahí siguen. Esto las separa sin volver a consultar
los sitios y sin perder el historial, porque los precios cuelgan de la variante y la
variante se muda entera al producto nuevo.

Solo actúa donde la regla de marca es concluyente: dos variantes cuyos nombres declaran
marcas reconocidas y no comparten ninguna. Si alguna no declara marca, la regla se
abstiene y el grupo se deja como está, que es lo mismo que haría el emparejamiento.

Uso:
    python src/reagrupar.py             # muestra qué separaría, sin tocar nada
    python src/reagrupar.py --aplicar   # lo hace
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import select  # noqa: E402

from emparejar import marcas, normalizar  # noqa: E402
from modelo import Producto, VariantePorCadena, crear_sesion  # noqa: E402


def grupos_mezclados(sesion):
    """Productos cuyas variantes declaran marcas reconocidas e incompatibles."""
    filas = sesion.execute(
        select(VariantePorCadena.producto_id, VariantePorCadena.id,
               VariantePorCadena.nombre_en_cadena)
    ).all()
    por_producto = defaultdict(list)
    for producto_id, variante_id, nombre in filas:
        por_producto[producto_id].append((variante_id, nombre))

    mezclados = []
    for producto_id, variantes in por_producto.items():
        if len(variantes) < 2:
            continue
        # Se agrupan las variantes por la marca que declaran. Las que no declaran
        # ninguna quedan aparte: la regla se abstiene con ellas y no justifican separar.
        por_marca = defaultdict(list)
        sin_marca = []
        for variante_id, nombre in variantes:
            encontradas = marcas(nombre)
            if encontradas:
                por_marca[frozenset(encontradas)].append((variante_id, nombre))
            else:
                sin_marca.append((variante_id, nombre))
        if len(por_marca) < 2:
            continue
        # Dos conjuntos de marcas que comparten alguna no son incompatibles.
        claves = list(por_marca)
        if any(a & b for i, a in enumerate(claves) for b in claves[i + 1:]):
            continue
        mezclados.append((producto_id, por_marca, sin_marca))
    return mezclados


def separar(sesion, mezclados, aplicar: bool) -> int:
    """Deja el grupo mayor en el producto original y muda los demás a productos nuevos."""
    separados = 0
    for producto_id, por_marca, sin_marca in mezclados:
        original = sesion.get(Producto, producto_id)
        # El grupo que se queda es el más numeroso; en empate, el que coincide con el
        # nombre normalizado que ya tiene el producto, para no renombrarlo sin motivo.
        orden = sorted(
            por_marca.items(),
            key=lambda kv: (len(kv[1]),
                            any(normalizar(n) == original.nombre_normalizado
                                for _, n in kv[1])),
            reverse=True,
        )
        se_queda, se_mudan = orden[0], orden[1:]
        print(f"\n  producto {producto_id} [{original.categoria}]")
        print(f"    se queda  {sorted(se_queda[0])}: "
              f"{se_queda[1][0][1][:62]}")
        for marca, variantes in se_mudan:
            print(f"    se separa {sorted(marca)}: {variantes[0][1][:62]}")
            if not aplicar:
                continue
            nuevo = Producto(
                nombre_normalizado=normalizar(variantes[0][1]),
                categoria=original.categoria,
                formato_unidad=original.formato_unidad,
                formato_cantidad=original.formato_cantidad,
                variantes=original.variantes,
            )
            sesion.add(nuevo)
            sesion.flush()
            for variante_id, _ in variantes:
                sesion.get(VariantePorCadena, variante_id).producto_id = nuevo.id
            separados += 1
    return separados


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true",
                    help="escribe los cambios; sin esto solo los muestra")
    args = ap.parse_args()

    Sesion = crear_sesion()
    with Sesion() as sesion:
        mezclados = grupos_mezclados(sesion)
        print(f"grupos con marcas incompatibles: {len(mezclados)}")
        separados = separar(sesion, mezclados, args.aplicar)
        if args.aplicar:
            sesion.commit()
            print(f"\nSe crearon {separados} productos. Los precios siguen a su variante.")
        else:
            print("\nNada se escribió. Repite con --aplicar para hacerlo.")


if __name__ == "__main__":
    main()
