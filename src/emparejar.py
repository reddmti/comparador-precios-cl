"""
Emparejamiento de productos equivalentes entre cadenas.

El nombre de un mismo producto cambia entre tiendas ("Aceite de Maravilla Miraflores
900 ml" y "Aceite miraflores maravilla botella 900 cc"), así que la comparación se hace
en dos partes:

1. El formato (cantidad + unidad) se extrae del nombre y se lleva a una unidad base
   (ml o g). Dos productos con formatos distintos nunca son el mismo producto, de modo
   que el formato actúa como filtro previo y no como parte del texto a comparar.
2. El resto del nombre se normaliza (minúsculas, sin tildes, sin palabras de relleno) y
   se compara con token_sort_ratio, que ordena las palabras antes de medir la similitud
   y por eso tolera el distinto orden entre cadenas.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Optional

from rapidfuzz import fuzz

# Unidades equivalentes llevadas a ml (volumen) o g (peso)
_A_BASE = {
    "l": ("ml", 1000), "lt": ("ml", 1000), "lts": ("ml", 1000), "litro": ("ml", 1000),
    "litros": ("ml", 1000), "ml": ("ml", 1), "cc": ("ml", 1), "cm3": ("ml", 1),
    "kg": ("g", 1000), "kilo": ("g", 1000), "kilos": ("g", 1000), "k": ("g", 1000),
    "g": ("g", 1), "gr": ("g", 1), "grs": ("g", 1), "gramos": ("g", 1),
}
_FORMATO = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(" + "|".join(sorted(_A_BASE, key=len, reverse=True)) + r")\b"
)

# Palabras que no distinguen un producto de otro
_RELLENO = {
    "de", "del", "la", "el", "los", "las", "con", "sin", "para", "en", "y", "a",
    "botella", "bolsa", "caja", "pack", "envase", "unidad", "un", "uds", "doypack",
    "sachet", "frasco", "pote", "tarro", "lata", "bidon", "estuche",
}

# Variantes que cambian el producto aunque el nombre se parezca
VARIANTES = [
    "integral", "sin lactosa", "deslactosada", "descremada", "semidescremada", "entera",
    "light", "zero", "cero", "diet", "sin azucar", "sin gluten", "organico", "organica",
    "grado 1", "grado 2", "g1", "g2", "tricolor", "al huevo", "instantaneo",
    "descafeinado", "vainilla", "chocolate", "frutilla",
    # Tipos que designan productos distintos aunque compartan marca y formato.
    # Se incorporaron al revisar las mayores diferencias de precio de la canasta (E3).
    "para freir", "freir", "canola", "maravilla", "oliva", "vegetal", "soya", "pepita de uva",
    "antisarro", "whitening", "blanqueador", "suavizante", "matic", "polvo", "liquido",
    # Formas de pasta: son productos distintos de la misma marca y formato, y el texto
    # restante es casi idéntico. «Cabellitos Lucchetti 400 g» y «Canutos Lucchetti
    # 400 g» alcanzan 81 de similitud y quedaban agrupados. Se usan raíces para que
    # tomen singular y plural, y «corbat» para que «corbatas» y «corbatitas» cuenten
    # como la misma forma.
    "cabellit", "canut", "corbat", "espiral", "mostachol", "tallarin", "spaghetti",
    "fettuccin", "penne", "rigatoni", "farfalle", "fusilli", "caracol", "dedalit",
    "quifaro", "lasan", "codit", "pantruca", "ravioli", "quinoa",
    # Las harinas se venden con y sin polvos de hornear, y no son intercambiables.
    # Como «sin» y «con» son palabras de relleno, ambos nombres se normalizan igual y
    # alcanzaban 100 de similitud. Estas dos entradas los separan sin tocar la
    # normalización, igual que «sin lactosa» o «sin azucar». Se usa la forma corta
    # porque Unimarc abrevia a «sin polvos» lo que Jumbo escribe completo.
    "sin polvos", "con polvos",
    # Variedades que distinguen el producto dentro de la misma marca y formato, y que
    # aparecieron al revisar las mayores diferencias de precio de la carga del
    # 08-nov-2026: «Arroz Basmati Tucapel 400 g» se emparejaba con «Arroz para sushi
    # tucapel 400 gr», y la harina P.A.N. dulce con la blanca. Se usan raíces para que
    # «amarillo» y «amarilla» cuenten como la misma variedad.
    "basmati", "sushi", "dulce", "blanc", "amarill",
]


# Marcas reconocidas en las veinte categorías obtenidas, en forma normalizada.
#
# Dos productos de marcas distintas no son el mismo producto aunque coincidan el
# formato, la variante y casi todo el texto: «Leche Soprole Sin Lactosa Entera 1 L» y
# «Leche entera surlat sin lactosa 1 l» tienen 81 de similitud, el mismo formato y las
# mismas variantes, y son productos diferentes.
#
# El listado se construyó recorriendo los nombres del conjunto obtenido y aplicando un
# criterio fijo: se incluyen marcas de fabricante y marcas propias de cadena; se excluyen
# líneas de producto de una misma marca («Tucapel Blue», «Miraflores Primavera»),
# descriptores («gourmet», «especial», «premium»), tipos («basmati», «arabica») y orígenes
# («española», «colombia»). Las marcas propias importan: la revisión manual trató
# Cuisine & Co (Cencosud) y Máxima (Unimarc) como productos distintos aunque el contenido
# sea equivalente, y esta regla reproduce ese criterio.
MARCAS = [
    # Despensa
    "miraflores", "tucapel", "banquete", "iansa", "campesino", "coliseo", "specia",
    "chef", "belmont", "natura", "huasco", "olitalia", "montecristo", "kardamili",
    # «La Española» y «Las Doscientas» son marcas de aceite de oliva, no orígenes:
    # se agregaron al revisar los pares de la canasta, que emparejaba La Española con
    # Banquete por 82 de similitud. Tras normalizar quedan en una sola palabra.
    "espanola", "doscientas",
    "lobos", "carmencita", "biosal", "collico", "mont blanc", "ambrosoli",
    # Conservas y salsas
    "robinson crusoe", "van camp", "san jose", "angelmo", "hellmann", "kraft",
    "alacena", "traverso", "mayodeli", "watt", "quilvo", "dalfour",
    # Pastas
    "lucchetti", "carozzi", "talliani", "trattoria",
    # Lácteos
    "soprole", "colun", "surlat", "loncoleche", "nido", "danone", "quillayes",
    # Desayuno
    "nescafe", "dolca", "juan valdez", "monterrey", "cruzeiro", "premier", "marley",
    "twinings", "lipton", "dilmah", "mildred", "mystic", "supremo",
    "zucaritas", "zucosos", "trix", "milo", "kellogg", "chocapic", "krispis",
    "fitness", "cola cao", "nestle",
    # Galletas
    "triton", "nik", "mckay", "kuky", "frac", "criollitas", "oreo", "costa", "arcor",
    "selz", "dulcita", "rigochoc", "alteza",
    # Limpieza
    "omo", "ariel", "drive", "rinso", "quix", "downy", "comfort", "popeye", "igenix",
    "fuzol",
    # Cuidado personal
    "dove", "palmolive", "elite", "ballerina", "trianon", "sancy", "simond", "simonds",
    "kadus", "pantene", "head shoulders", "sedal", "elvive", "fructis",
    "herbal essences", "tresemme", "umai", "familand",
    "colgate", "sensodyne", "pepsodent", "oral b", "aquafresh",
    "scott", "confort", "favorita", "noble", "swan",
    # Marcas propias de cadena: no son el mismo producto entre cadenas
    "cuisine", "maxima", "merkat", "nuestra cocina", "acuenta", "great value",
    "smart clean",
]
_MARCAS = [tuple(m.split()) for m in MARCAS]


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


_UNIDADES = re.compile(r"(\d+)\s*(?:u|un|uds?|unidades)\b")
# Solo se multiplica cuando el nombre declara un envase múltiple de forma explícita:
# "Pack 12 un. ... 1 L" o "9 un de 24 g". En cambio, "Té 100 un. Caja 200 g" cuenta
# bolsitas dentro de una caja de 200 g y multiplicar duplicaría la cantidad.
_ES_PACK = re.compile(r"pack|\d+\s*(?:u|un|uds?|unidades)\s*[.,]?\s*de\b", re.I)


def unidades_envase(nombre: str) -> int:
    """Cuántas unidades trae el envase; 1 si no declara ser un envase múltiple."""
    limpio = sin_tildes(nombre).lower()
    if not _ES_PACK.search(limpio):
        return 1
    m = _UNIDADES.search(limpio)
    return int(m.group(1)) if m else 1


def formato(nombre: str) -> Optional[tuple[str, float]]:
    """
    Devuelve (unidad_base, cantidad total) del formato declarado en el nombre.

    La cantidad es la del envase completo: un pack de 12 unidades de 1 L son 12.000 ml,
    de modo que no se confunde con una botella suelta de 1 L y el precio del pack queda
    asociado a la cantidad que realmente contiene.
    """
    m = _FORMATO.search(sin_tildes(nombre).lower())
    if not m:
        return None
    # En Chile el punto separa miles y la coma es decimal: "1.350 g" son 1350 g y
    # "1,5 L" es 1,5 L. Un punto seguido de exactamente tres dígitos es separador de miles.
    crudo = m.group(1)
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", crudo):
        cantidad = float(crudo.replace(".", ""))
    else:
        cantidad = float(crudo.replace(",", "."))
    unidad, factor = _A_BASE[m.group(2)]
    return unidad, round(cantidad * factor * unidades_envase(nombre), 2)


def normalizar(nombre: str) -> str:
    """Nombre en minúsculas, sin tildes, sin formato y sin palabras de relleno."""
    t = sin_tildes(nombre).lower()
    t = _FORMATO.sub(" ", t)
    t = re.sub(r"[^a-z0-9%\s]", " ", t)
    # Los números se conservan aunque sean de un dígito: distinguen "grado 1" de
    # "grado 2" y "spaghetti n°3" de "n°5".
    palabras = [p for p in t.split() if p not in _RELLENO and (len(p) > 1 or p.isdigit())]
    # Una palabra repetida (la marca suele ir en el nombre y en la marca) no aporta
    vistas, limpio = set(), []
    for p in palabras:
        if p not in vistas:
            vistas.add(p)
            limpio.append(p)
    return " ".join(limpio)


def numeros(nombre: str) -> frozenset[str]:
    """Números que quedan en el nombre una vez quitado el formato.

    Distinguen productos que el texto no separa: «Spaghetti N°3» y «Spaghetti N°5»
    tienen 96 de similitud y las mismas variantes, pero no son el mismo producto.
    """
    return frozenset(re.findall(r"\b\d+\b", normalizar(nombre)))


def variantes(nombre: str) -> frozenset[str]:
    t = sin_tildes(nombre).lower()
    return frozenset(v for v in VARIANTES if v in t)


def marcas(nombre: str) -> frozenset[str]:
    """
    Marcas reconocidas en el nombre.

    La comparación es por secuencia de palabras y no por subcadena: «natural» no debe
    activar la marca «Natura», ni «confortable» la marca «Confort».
    """
    palabras = tuple(normalizar(nombre).split())
    encontradas = set()
    for marca in _MARCAS:
        n = len(marca)
        if any(palabras[i:i + n] == marca for i in range(len(palabras) - n + 1)):
            encontradas.add(" ".join(marca))
    return frozenset(encontradas)


def marcas_compatibles(nombre_a: str, nombre_b: str) -> bool:
    """
    Si ambos nombres declaran marca, tienen que compartir al menos una.

    Cuando en alguno de los dos no se reconoce ninguna marca la regla no opina: el
    nombre no alcanza para decidir y descartar el par introduciría más falsos negativos
    que aciertos. Basta con que compartan una marca, de modo que «Arroz Miraflores
    Primavera» y «Arroz Miraflores» siguen siendo compatibles.
    """
    ma, mb = marcas(nombre_a), marcas(nombre_b)
    if not ma or not mb:
        return True
    return bool(ma & mb)


@dataclass(frozen=True)
class Candidato:
    a: str          # nombre en la cadena A
    b: str          # nombre en la cadena B
    score: float    # similitud 0-100
    formato_igual: bool
    variantes_iguales: bool
    numeros_iguales: bool
    # Con valor por omisión para no alterar el orden posicional del resto
    marcas_compatibles: bool = True


def similitud(nombre_a: str, nombre_b: str) -> float:
    return fuzz.token_sort_ratio(normalizar(nombre_a), normalizar(nombre_b))


def candidatos(productos_a: Iterable[dict], productos_b: Iterable[dict],
               exigir_formato: bool = True) -> list[Candidato]:
    """
    Mejor candidato de B para cada producto de A.

    Con exigir_formato, solo se comparan productos cuyo formato coincide; eso reduce
    las comparaciones de |A|x|B| a la suma de |A_f|x|B_f| por formato f.
    """
    por_formato: dict[object, list[dict]] = {}
    for p in productos_b:
        por_formato.setdefault(formato(p["nombre"]) if exigir_formato else None, []).append(p)

    salida = []
    for pa in productos_a:
        clave = formato(pa["nombre"]) if exigir_formato else None
        grupo = por_formato.get(clave, [])
        mejor, mejor_score = None, -1.0
        for pb in grupo:
            s = similitud(pa["nombre"], pb["nombre"])
            if s > mejor_score:
                mejor, mejor_score = pb, s
        if mejor is not None:
            salida.append(Candidato(
                a=pa["nombre"], b=mejor["nombre"], score=mejor_score,
                formato_igual=formato(pa["nombre"]) == formato(mejor["nombre"]),
                variantes_iguales=variantes(pa["nombre"]) == variantes(mejor["nombre"]),
                numeros_iguales=numeros(pa["nombre"]) == numeros(mejor["nombre"]),
                marcas_compatibles=marcas_compatibles(pa["nombre"], mejor["nombre"]),
            ))
    return salida
