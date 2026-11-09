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
from sqlalchemy import case, func, select

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

# Una diferencia de más de cinco veces entre dos cadenas para el mismo producto no es
# una diferencia de precio, es un error de lectura. La mayor diferencia legítima medida
# en la evaluación fue de 1,9 veces (89,7%), así que el tope no descarta casos reales y
# evita que la portada destaque justamente los datos malos: ordenar por diferencia
# relativa los pone primero. Dos de los 2.521 precios cargados el 20-oct-2026 eran de
# este tipo, por el precio por metro del papel higiénico que la extracción ya corrige.
RAZON_INVEROSIMIL = 5.0


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
    imagen_url: str | None = None
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
    # Foto del producto: la primera que alguna cadena publique. Es indistinto cuál,
    # porque es el mismo artículo; se prefiere la que exista a no mostrar nada.
    imagen_url: str | None = None
    precios: list[PrecioCadena]
    menor_precio: int | None = None
    mayor_precio: int | None = None
    ahorro: int | None = None
    cadena_mas_barata: str | None = None


class Categoria(BaseModel):
    nombre: str
    productos: int
    comparables: int   # con precio en dos o más cadenas
    imagen_url: str | None = None   # foto de muestra, para reconocerla de un vistazo


class PaginaProductos(BaseModel):
    """Una página de resultados. `total` es el largo completo, no el de la página."""
    total: int
    comparables: int
    items: list[ProductoComparado]


class Sugerencia(BaseModel):
    producto_id: int
    nombre: str
    categoria: str
    cadenas: int


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


class ItemComparado(BaseModel):
    """Una línea de la lista, con lo que se escribió y lo que se encontró."""
    texto: str
    cantidad: int
    producto: ProductoComparado | None = None
    entra_al_total: bool = False
    cadenas_que_faltan: list[str] = Field(default_factory=list)


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
    # Cada línea escrita, en el orden en que se escribió
    items: list[ItemComparado] = Field(default_factory=list)
    # Comprando cada producto donde está más barato, sobre la misma canasta comparable
    total_optimo: int = 0
    optimo_vs_mas_barata: int = 0
    optimo_vs_mas_cara: int = 0


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
               VariantePorCadena.url_producto, VariantePorCadena.imagen_url,
               Precio.fecha_registro)
        .join(VariantePorCadena, VariantePorCadena.id == Precio.variante_id)
        .join(Cadena, Cadena.id == VariantePorCadena.cadena_id)
        .join(ultima, (ultima.c.variante_id == Precio.variante_id)
                      & (ultima.c.fecha == Precio.fecha_registro))
        .where(VariantePorCadena.producto_id.in_(producto_ids))
    ).all()

    # Un producto puede tener más de una variante de la misma cadena, y entonces la
    # comparación mostraría dos filas para esa cadena. Ocurre por dos motivos: la tienda
    # publica el mismo artículo dos veces con redacciones que se normalizan igual
    # («200 cc» y «200 ml», «Tarro 170 g» y «Frasco 170 g»), o el emparejamiento agrupó
    # de más. En ambos casos la respuesta correcta a «cuánto cuesta en esta cadena» es el
    # menor de los precios que esa cadena ofrece: 25 de los 1.796 productos cargados el
    # 20-oct-2026 estaban en esta situación.
    por_cadena: dict[int, dict[str, PrecioCadena]] = defaultdict(dict)
    for pid, cadena, precio, por_unidad, nombre, url, imagen, fecha in filas:
        dato = PrecioCadena(
            cadena=cadena, precio=precio, precio_por_unidad=por_unidad,
            nombre_en_cadena=nombre, url=url, imagen_url=imagen, fecha=fecha)
        previo = por_cadena[pid].get(cadena)
        if previo is None or dato.precio < previo.precio:
            por_cadena[pid][cadena] = dato

    agrupado: dict[int, list[PrecioCadena]] = {
        pid: sorted(datos.values(), key=lambda x: x.precio)
        for pid, datos in por_cadena.items()
    }
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
        imagen_url=next((p.imagen_url for p in precios if p.imagen_url), None),
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


@app.get("/categorias", response_model=list[Categoria],
         summary="Categorías disponibles con su cantidad de productos")
def categorias(sesion=Depends(obtener_sesion)):
    """
    Las categorías son las consultas con que se obtuvieron los productos.

    Se informa aparte cuántos son comparables, es decir con precio en dos o más
    cadenas: una categoría con muchos productos pero pocos comparables sirve de poco
    para quien quiere comparar, y conviene que la interfaz pueda distinguirlo.
    """
    cadenas_por_producto = (
        select(VariantePorCadena.producto_id,
               func.count(func.distinct(VariantePorCadena.cadena_id)).label("n"))
        .group_by(VariantePorCadena.producto_id).subquery()
    )
    filas = sesion.execute(
        select(Producto.categoria, func.count(Producto.id),
               func.sum(case((cadenas_por_producto.c.n > 1, 1), else_=0)))
        .join(cadenas_por_producto, cadenas_por_producto.c.producto_id == Producto.id)
        .group_by(Producto.categoria).order_by(Producto.categoria)
    ).all()
    # Una foto por categoría, tomada de un producto que esté en más de una cadena: son
    # los que de verdad sirven para comparar, y además suelen ser los más conocidos.
    muestras: dict[str, str] = {}
    for categoria, imagen in sesion.execute(
        select(Producto.categoria, VariantePorCadena.imagen_url)
        .join(VariantePorCadena, VariantePorCadena.producto_id == Producto.id)
        .join(cadenas_por_producto, cadenas_por_producto.c.producto_id == Producto.id)
        .where(VariantePorCadena.imagen_url.is_not(None), cadenas_por_producto.c.n > 1)
    ).all():
        muestras.setdefault(categoria, imagen)

    return [Categoria(nombre=c, productos=n, comparables=int(k or 0),
                      imagen_url=muestras.get(c))
            for c, n, k in filas]


@app.get("/destacados", response_model=list[ProductoComparado],
         summary="Productos donde hoy hay más diferencia de precio entre cadenas")
def destacados(limite: int = Query(default=12, ge=1, le=50),
               categoria: str | None = Query(default=None),
               sesion=Depends(obtener_sesion)):
    """
    Dónde más se gana comparando hoy.

    Se ordena por diferencia relativa y no absoluta: $600 de diferencia en un producto
    de $700 le importa más a quien compra que los mismos $600 en uno de $9.000. Solo
    entran los productos con precio en al menos dos cadenas, porque en el resto no hay
    diferencia que mostrar.
    """
    consulta = select(Producto.id)
    if categoria:
        consulta = consulta.where(Producto.categoria == categoria)
    ids = sesion.execute(consulta).scalars().all()
    precios = precios_vigentes(sesion, list(ids))

    conmensurables = []
    for pid, lista in precios.items():
        if len(lista) < 2:
            continue
        menor, mayor = lista[0].precio, lista[-1].precio
        if menor <= 0 or mayor / menor > RAZON_INVEROSIMIL:
            continue
        conmensurables.append(((mayor - menor) / menor, pid))
    conmensurables.sort(reverse=True)

    elegidos = [pid for _, pid in conmensurables[:limite]]
    productos = {p.id: p for p in
                 sesion.execute(select(Producto).where(Producto.id.in_(elegidos))).scalars()}
    return [armar_comparacion(productos[pid], precios[pid]) for pid in elegidos if pid in productos]


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


@app.get("/sugerencias", response_model=list[Sugerencia],
         summary="Nombres de producto que empiezan o contienen lo que se escribe")
def sugerencias(q: str = Query(min_length=2, max_length=60),
                limite: int = Query(default=8, ge=1, le=20),
                sesion=Depends(obtener_sesion)):
    """
    Autocompletado del buscador.

    Se ordenan primero los productos presentes en más cadenas: quien escribe «lech»
    quiere comparar, y un producto que solo está en una cadena no le sirve para eso
    aunque su nombre calce igual de bien.
    """
    terminos = [x for x in normalizar(q).split() if x]
    if not terminos:
        return []
    consulta = select(Producto)
    for termino in terminos:
        consulta = consulta.where(Producto.nombre_normalizado.contains(termino))
    productos = sesion.execute(consulta.limit(60)).scalars().all()

    cuantas = dict(sesion.execute(
        select(VariantePorCadena.producto_id,
               func.count(func.distinct(VariantePorCadena.cadena_id)))
        .where(VariantePorCadena.producto_id.in_([p.id for p in productos]))
        .group_by(VariantePorCadena.producto_id)
    ).all())

    nombres = dict(sesion.execute(
        select(VariantePorCadena.producto_id, VariantePorCadena.nombre_en_cadena)
        .where(VariantePorCadena.producto_id.in_([p.id for p in productos]))
    ).all())

    filas = [
        Sugerencia(producto_id=p.id,
                   nombre=nombres.get(p.id, p.nombre_normalizado),
                   categoria=p.categoria,
                   cadenas=cuantas.get(p.id, 0))
        for p in productos
    ]
    filas.sort(key=lambda s: (-s.cadenas, len(s.nombre)))
    return filas[:limite]


@app.get("/productos", response_model=PaginaProductos,
         summary="Lista productos de una categoría o de una búsqueda, ordenados")
def listar_productos(
    q: str | None = Query(default=None, max_length=80),
    categoria: str | None = Query(default=None, max_length=80),
    orden: str = Query(default="diferencia", pattern="^(diferencia|precio|nombre)$"),
    solo_comparables: bool = Query(default=False),
    cadena: str | None = Query(default=None, max_length=40),
    limite: int = Query(default=24, ge=1, le=200),
    desde: int = Query(default=0, ge=0),
    sesion=Depends(obtener_sesion),
):
    """
    El listado que usan la pantalla de categoría y la de resultados de búsqueda.

    Ordenar por diferencia obliga a conocer el precio de todos los productos que
    califican antes de recortar la página, de modo que el filtro se aplica en la base
    y el orden en Python. Una categoría tiene del orden de cien productos, así que el
    costo es acotado; el filtro por categoría es justamente lo que lo mantiene así.
    """
    consulta = select(Producto)
    if categoria:
        consulta = consulta.where(Producto.categoria == categoria)
    for termino in [x for x in normalizar(q or "").split() if x]:
        consulta = consulta.where(Producto.nombre_normalizado.contains(termino))
    productos = sesion.execute(consulta).scalars().all()

    precios = precios_vigentes(sesion, [p.id for p in productos])
    filas = []
    for producto in productos:
        lista = precios.get(producto.id, [])
        if solo_comparables and len(lista) < 2:
            continue
        # Filtrar por cadena responde a «qué puedo comprar en la que me queda cerca»,
        # que es distinto de comparar: se conservan todos los precios del producto para
        # que siga viéndose cuánto cuesta en las demás.
        if cadena and not any(x.cadena == cadena for x in lista):
            continue
        diferencia = 0.0
        if len(lista) >= 2:
            menor, mayor = lista[0].precio, lista[-1].precio
            # Mismo resguardo que en /destacados: una razón imposible es un error de
            # lectura, y ordenar por diferencia lo pondría primero. Se lista igual,
            # pero sin premiarlo con el primer lugar.
            if menor > 0 and mayor / menor <= RAZON_INVEROSIMIL:
                diferencia = (mayor - menor) / menor
        filas.append((producto, lista, diferencia))

    if orden == "precio":
        filas.sort(key=lambda f: f[1][0].precio if f[1] else 10**9)
    elif orden == "nombre":
        filas.sort(key=lambda f: f[0].nombre_normalizado)
    else:
        filas.sort(key=lambda f: f[2], reverse=True)

    pagina = filas[desde:desde + limite]
    return PaginaProductos(
        total=len(filas),
        comparables=sum(1 for _, lista, _ in filas if len(lista) > 1),
        items=[armar_comparacion(producto, lista) for producto, lista, _ in pagina],
    )


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
    por_texto: dict[str, Producto] = {}
    for item in entrada.items:
        producto = emparejar_texto(sesion, item.texto)
        sesion.add(ItemLista(lista_id=lista.id, texto_original=item.texto,
                             producto_id=producto.id if producto else None,
                             cantidad=item.cantidad))
        if producto:
            reconocidos.append((producto, item.cantidad))
            por_texto[item.texto] = producto
        else:
            no_reconocidos.append(item.texto)
    sesion.commit()

    precios = precios_vigentes(sesion, [p.id for p, _ in reconocidos])
    cadenas_activas = {c for lista_p in precios.values() for c in (x.cadena for x in lista_p)}

    # Un producto entra al total solo si tiene precio en todas las cadenas: de lo
    # contrario se compararían canastas distintas y la cadena con menos cobertura
    # aparecería como la más barata por el solo hecho de tener menos productos.
    comparables, sin_comparacion = [], []
    detalle_items: list[ItemComparado] = []
    for item in entrada.items:
        par = por_texto.get(item.texto)
        if par is None:
            detalle_items.append(ItemComparado(texto=item.texto, cantidad=item.cantidad))
            continue
        producto = par
        disponibles = {x.cadena for x in precios.get(producto.id, [])}
        entra = bool(cadenas_activas) and disponibles == cadenas_activas
        if entra:
            comparables.append((producto, item.cantidad))
        else:
            faltan = ", ".join(sorted(cadenas_activas - disponibles)) or "ninguna cadena"
            visibles = precios.get(producto.id, [])
            nombre = min((x.nombre_en_cadena for x in visibles), key=len,
                         default=producto.nombre_normalizado)
            sin_comparacion.append(f"{nombre} (sin precio en {faltan})")
        detalle_items.append(ItemComparado(
            texto=item.texto, cantidad=item.cantidad,
            producto=armar_comparacion(producto, precios.get(producto.id, [])),
            entra_al_total=entra,
            cadenas_que_faltan=sorted(cadenas_activas - disponibles),
        ))

    totales: dict[str, int] = defaultdict(int)
    for producto, cantidad in comparables:
        for p in precios.get(producto.id, []):
            totales[p.cadena] += p.precio * cantidad

    recomendada = min(totales, key=totales.get) if totales else None
    ahorro = (max(totales.values()) - min(totales.values())) if totales else 0

    # Comprar cada producto donde está más barato: es la cifra que justifica comparar
    # producto a producto en vez de elegir una sola cadena, y en la medición de la
    # evaluación resultó siete veces mayor que elegir la cadena más barata.
    optimo = sum(min(p.precio for p in precios[producto.id]) * cantidad
                 for producto, cantidad in comparables if precios.get(producto.id))

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
        items=detalle_items,
        total_optimo=optimo,
        optimo_vs_mas_barata=(min(totales.values()) - optimo) if totales else 0,
        optimo_vs_mas_cara=(max(totales.values()) - optimo) if totales else 0,
    )
