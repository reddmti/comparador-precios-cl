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
]


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


@dataclass(frozen=True)
class Candidato:
    a: str          # nombre en la cadena A
    b: str          # nombre en la cadena B
    score: float    # similitud 0-100
    formato_igual: bool
    variantes_iguales: bool
    numeros_iguales: bool


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
            ))
    return salida
