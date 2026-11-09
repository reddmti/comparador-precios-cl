"""
Modelo de datos y conexión.

La conexión se toma de la variable de entorno DATABASE_URL. Si no está definida se
usa un archivo SQLite local, de modo que el sistema corra sin configurar nada; con la
cadena de Supabase apuntando a PostgreSQL, el mismo código funciona sin cambios.
"""

import os
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric,
    SmallInteger, String, Text, UniqueConstraint, create_engine, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

# Ruta absoluta: así la base es la misma se ejecute desde donde se ejecute
ARCHIVO_LOCAL = Path(__file__).resolve().parents[1] / "comparador.db"
URL_POR_DEFECTO = f"sqlite:///{ARCHIVO_LOCAL.as_posix()}"


def url_base_datos() -> str:
    url = os.environ.get("DATABASE_URL", URL_POR_DEFECTO)
    # Supabase entrega la cadena como postgres://, que SQLAlchemy 2 ya no reconoce
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


class Base(DeclarativeBase):
    pass


class Cadena(Base):
    __tablename__ = "cadenas"

    # SQLite solo autoincrementa claves INTEGER, por eso no se usa SmallInteger aquí
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    url_base: Mapped[str] = mapped_column(String(200))
    activa: Mapped[bool] = mapped_column(default=True)


class Producto(Base):
    """Entidad conceptual: el producto, independiente de la cadena que lo venda."""

    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_normalizado: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(80))
    # Formato en unidad base (ml o g) y cantidad total del envase
    formato_unidad: Mapped[str | None] = mapped_column(String(4), nullable=True)
    formato_cantidad: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    # Variantes ordenadas y unidas por "|", para que sea portable entre motores
    variantes: Mapped[str] = mapped_column(Text, default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    variantes_cadena: Mapped[list["VariantePorCadena"]] = relationship(
        back_populates="producto", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("nombre_normalizado", "formato_unidad", "formato_cantidad",
                         "variantes", name="uq_producto"),
        Index("idx_productos_categoria", "categoria"),
    )


class VariantePorCadena(Base):
    """Cómo un producto aparece en una cadena concreta, con su nombre y enlace propios."""

    __tablename__ = "variantes_por_cadena"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id", ondelete="CASCADE"))
    cadena_id: Mapped[int] = mapped_column(ForeignKey("cadenas.id", ondelete="CASCADE"))
    nombre_en_cadena: Mapped[str] = mapped_column(Text)
    url_producto: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Dirección de la foto en el servidor de la propia cadena. Se guarda la dirección y
    # nunca el archivo: la imagen la sirve la cadena a quien visita el comparador, de
    # modo que aquí no se almacena ni se redistribuye material de terceros.
    imagen_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Similitud con la que se asoció al producto; permite auditar el emparejamiento
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    producto: Mapped[Producto] = relationship(back_populates="variantes_cadena")
    cadena: Mapped[Cadena] = relationship()
    precios: Mapped[list["Precio"]] = relationship(
        back_populates="variante", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("cadena_id", "nombre_en_cadena", name="uq_variante"),
        Index("idx_variantes_producto", "producto_id"),
    )


class Precio(Base):
    """Observación de precio: una por variante y día."""

    __tablename__ = "precios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    variante_id: Mapped[int] = mapped_column(ForeignKey("variantes_por_cadena.id", ondelete="CASCADE"))
    precio: Mapped[int] = mapped_column(Integer)
    precio_por_unidad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_registro: Mapped[date] = mapped_column(Date, default=date.today)

    variante: Mapped[VariantePorCadena] = relationship(back_populates="precios")

    __table_args__ = (
        UniqueConstraint("variante_id", "fecha_registro", name="uq_precio_dia"),
        CheckConstraint("precio > 0", name="ck_precio_positivo"),
        Index("idx_precios_variante_fecha", "variante_id", "fecha_registro"),
    )


class Lista(Base):
    """Lista de compras de una sesión anónima: el sistema no guarda datos personales."""

    __tablename__ = "listas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sesion_id: Mapped[str] = mapped_column(String(64))
    creada_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["ItemLista"]] = relationship(
        back_populates="lista", cascade="all, delete-orphan")


class ItemLista(Base):
    __tablename__ = "items_lista"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lista_id: Mapped[int] = mapped_column(ForeignKey("listas.id", ondelete="CASCADE"))
    texto_original: Mapped[str] = mapped_column(Text)
    # Opcional: parte de los ítems que escribe el usuario no tendrá producto asociado
    producto_id: Mapped[int | None] = mapped_column(
        ForeignKey("productos.id", ondelete="SET NULL"), nullable=True)
    cantidad: Mapped[int] = mapped_column(SmallInteger, default=1)

    lista: Mapped[Lista] = relationship(back_populates="items")
    producto: Mapped[Producto | None] = relationship()


CADENAS_INICIALES = [
    ("Jumbo", "https://www.jumbo.cl"),
    ("Santa Isabel", "https://www.santaisabel.cl"),
    ("Unimarc", "https://www.unimarc.cl"),
]


def crear_sesion(url: str | None = None, echo: bool = False):
    """Crea el esquema si no existe, siembra las cadenas y devuelve una fábrica de sesiones."""
    url = url or url_base_datos()
    opciones = {}
    if os.environ.get("VERCEL"):
        # En un entorno sin servidor cada invocación es un proceso distinto: mantener
        # un pool propio agotaría las conexiones de la base. El pooler de Supabase ya
        # cumple ese rol.
        from sqlalchemy.pool import NullPool
        opciones["poolclass"] = NullPool
    motor = create_engine(url, echo=echo, future=True, **opciones)
    if not os.environ.get("VERCEL"):
        Base.metadata.create_all(motor)
    Sesion = sessionmaker(motor, expire_on_commit=False)
    with Sesion() as s:
        if s.query(Cadena).count() == 0:
            s.add_all([Cadena(nombre=n, url_base=u) for n, u in CADENAS_INICIALES])
            s.commit()
    return Sesion
