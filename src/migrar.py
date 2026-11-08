"""
Copia los datos de la base local a la base remota.

Evita volver a consultar los sitios de las cadenas y repetir el emparejamiento: lo que
ya se calculó en local se traslada tal cual, conservando los identificadores para que
las relaciones entre tablas se mantengan.

Uso:
    python src/migrar.py                      # de comparador.db a DATABASE_URL
    python src/migrar.py --origen otra.db
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import create_engine, func, insert, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from modelo import (  # noqa: E402
    ARCHIVO_LOCAL, Base, Cadena, ItemLista, Lista, Precio, Producto,
    VariantePorCadena, url_base_datos,
)

# El orden importa: una tabla se copia después de aquellas a las que referencia.
TABLAS = [Cadena, Producto, VariantePorCadena, Precio, Lista, ItemLista]
LOTE = 500


def cargar_env(ruta: Path) -> None:
    """Lee un archivo .env simple sin depender de otra biblioteca."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip())


def filas(sesion, tabla) -> list[dict]:
    columnas = [c.name for c in tabla.__table__.columns]
    return [dict(zip(columnas, fila)) for fila in
            sesion.execute(select(*[tabla.__table__.c[c] for c in columnas])).all()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra la base local a la remota")
    parser.add_argument("--origen", default=str(ARCHIVO_LOCAL), help="archivo SQLite de origen")
    parser.add_argument("--vaciar", action="store_true",
                        help="borra el contenido del destino antes de copiar")
    args = parser.parse_args()

    cargar_env(Path(__file__).resolve().parents[1] / ".env")
    destino_url = url_base_datos()
    if destino_url.startswith("sqlite"):
        raise SystemExit("DATABASE_URL no está definida: el destino sería la misma base local")

    origen = create_engine(f"sqlite:///{Path(args.origen).resolve().as_posix()}", future=True)
    destino = create_engine(destino_url, future=True)
    Base.metadata.create_all(destino)
    print(f"Destino preparado: {destino_url.split('@')[-1]}")

    SesionOrigen = sessionmaker(origen)
    SesionDestino = sessionmaker(destino)

    with SesionOrigen() as o, SesionDestino() as d:
        if args.vaciar:
            for tabla in reversed(TABLAS):
                d.execute(tabla.__table__.delete())
            d.commit()

        for tabla in TABLAS:
            datos = filas(o, tabla)
            existentes = d.execute(select(func.count()).select_from(tabla.__table__)).scalar()
            if existentes:
                print(f"  {tabla.__tablename__:22} ya tenía {existentes} filas, se omite")
                continue
            for i in range(0, len(datos), LOTE):
                d.execute(insert(tabla.__table__), datos[i:i + LOTE])
            d.commit()
            print(f"  {tabla.__tablename__:22} {len(datos):>5} filas copiadas")

        # Las secuencias de PostgreSQL quedan en 1 tras insertar con id explícito
        if destino_url.startswith("postgresql"):
            from sqlalchemy import text
            for tabla in TABLAS:
                d.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{tabla.__tablename__}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {tabla.__tablename__}), 1))"))
            d.commit()
            print("Secuencias de identificadores ajustadas")

    print("Migración terminada")


if __name__ == "__main__":
    main()
