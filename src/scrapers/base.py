"""
Interfaz base para todos los scrapers.
Agregar una tienda nueva = crear un archivo en scrapers/ que herede de BaseScraper
y decorarlo con @registry.register("NombreTienda").
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from playwright.async_api import Page


@dataclass
class Producto:
    nombre: str
    precio: Optional[float]
    tienda: str
    ean: Optional[str] = None
    url: Optional[str] = None
    precio_por_kg: Optional[float] = None
    imagen_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "precio": self.precio,
            "tienda": self.tienda,
            "ean": self.ean,
            "url": self.url,
            "precio_por_kg": self.precio_por_kg,
        }


class BaseScraper(ABC):
    """
    Cada tienda implementa este contrato.
    Solo hay que definir: nombre, search_url() y extraer().
    """

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Nombre legible de la tienda, ej: 'Jumbo'"""
        ...

    @abstractmethod
    def search_url(self, query: str) -> str:
        """URL de búsqueda para el query dado"""
        ...

    @abstractmethod
    async def extraer(self, page: Page, query: str) -> list[Producto]:
        """
        Recibe una Playwright Page ya navegada a search_url(query).
        Retorna la lista de productos encontrados.
        """
        ...

    async def scrape(self, page: Page, query: str) -> list[Producto]:
        """Punto de entrada — navega y extrae. No sobreescribir."""
        url = self.search_url(query)
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(4000)
        return await self.extraer(page, query)


# ---------------------------------------------------------------------------
# Lectura de tarjetas de producto
# ---------------------------------------------------------------------------

# Recorre cada tarjeta a partir de su elemento de nombre y devuelve su texto por líneas.
# Sube por el DOM hasta el primer ancestro que contiene un precio ("$"): esa es la tarjeta.
# Emparejar listas paralelas de nombres y precios por índice desalinea todo en cuanto
# una tarjeta trae una promoción o un segundo precio por kg.
JS_TARJETAS = r"""([selNombre, selMarca]) => {
    return [...document.querySelectorAll(selNombre)].map(el => {
        const nombre = el.innerText.trim();
        let card = el;
        while (card && !(card.innerText.includes('$') && card.innerText.length > nombre.length + 3)) card = card.parentElement;
        if (!card) return null;
        const marcaEl = selMarca ? card.querySelector(selMarca) : null;
        const link = [...card.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).find(h => h && !h.startsWith('#'))
            || (card.tagName === 'A' ? card.getAttribute('href') : null);
        const img = card.querySelector('img');
        return {
            nombre,
            marca: marcaEl ? marcaEl.innerText.trim() : '',
            lineas: card.innerText.split(String.fromCharCode(10)).map(l => l.trim()).filter(Boolean),
            url: link ? new URL(link, location.origin).href : location.href,
            imagen_url: img ? img.src : null,
        };
    }).filter(Boolean);
}"""

_MONTO = re.compile(r"\$\s*([\d.]+)")

# Precio por unidad de medida: "$2.625 x kg", "$874 x 100ml", "$417 x 100 ml", "$3.490 x un".
# La cantidad intermedia es opcional y la unidad puede ir pegada al número.
#
# La lista no se limita a peso y volumen: en papel higiénico, servilletas y toallas de
# papel Jumbo informa el precio por metro ("$19 x m") y a veces por rollo o por hoja.
# Mientras el metro faltó aquí, esa línea se leía como el precio del producto y dejaba
# papeles higiénicos a $16 y $20 (2 de los 2.521 precios cargados el 20-oct-2026).
# Las unidades largas conviven con las cortas porque el \b final obliga a reintentar:
# "x mts" no se queda en "m", igual que "x grs" nunca se quedó en "g".
_POR_UNIDAD = (r"x\s*\d*[.,]?\d*\s*"
               r"(kg|g|gr|grs|ml|cc|l|lt|lts|m|mt|mts|metro|metros|"
               r"un|u|uds?|unidad|unidades|rollo|rollos|hoja|hojas|"
               r"lavado|lavados|capsula|capsulas|bolsita|bolsitas)\b")
# Promociones: "Lleva 4 por $3.000", "4 x $3.000", "6 por 5 a $1.600", "2da a $990".
_PROMO = r"lleva|^\s*\d+\s*x\s*\$|\d+\s*por\s*\d+|\d+\s*(da|ra|ta)\s+a\s*\$"

# Líneas que traen un "$" pero no son el precio unitario del producto
_NO_UNITARIO = re.compile(f"{_POR_UNIDAD}|{_PROMO}|%", re.I)


def _monto(linea: str) -> Optional[float]:
    m = _MONTO.search(linea)
    return float(m.group(1).replace(".", "")) if m else None


def precios_de_tarjeta(lineas: list[str]) -> tuple[Optional[float], Optional[float]]:
    """
    Devuelve (precio_vigente, precio_por_kg) a partir del texto de una tarjeta.

    El precio vigente es el primer monto que no pertenece a una promoción
    ("Lleva 2 por $X", "4 x $X") ni a un precio por unidad de medida ("$X x kg").
    Si hay oferta, las tiendas muestran primero el precio rebajado y luego el normal,
    así que el primero es el que paga el cliente. El precio por kg es el que viene
    inmediatamente después de ese precio, no el de la promoción.
    """
    for i, linea in enumerate(lineas):
        if "$" not in linea or _NO_UNITARIO.search(linea):
            continue
        precio = _monto(linea)
        por_kg = None
        for siguiente in lineas[i + 1:i + 3]:
            if re.search(r"x\s*\d*\s*(kg|l|lt)\b", siguiente, re.I):
                por_kg = _monto(siguiente)
                break
        return precio, por_kg
    return None, None


def producto_desde_tarjeta(t: dict, tienda: str) -> Producto:
    precio, por_kg = precios_de_tarjeta(t["lineas"])
    marca, nombre = t.get("marca", ""), t["nombre"]
    if marca and marca.lower() not in nombre.lower():
        nombre = f"{marca} {nombre}"
    return Producto(nombre=nombre, precio=precio, tienda=tienda, url=t.get("url"),
                    precio_por_kg=por_kg, imagen_url=t.get("imagen_url"))


# ---------------------------------------------------------------------------
# Registro central — autodescubrimiento de scrapers
# ---------------------------------------------------------------------------

class ScraperRegistry:
    def __init__(self):
        self._scrapers: dict[str, type[BaseScraper]] = {}

    def register(self, nombre: str):
        """Decorador: @registry.register('Jumbo')"""
        def decorator(cls: type[BaseScraper]):
            self._scrapers[nombre] = cls
            return cls
        return decorator

    def get(self, nombre: str) -> BaseScraper:
        if nombre not in self._scrapers:
            raise KeyError(f"Scraper '{nombre}' no registrado. Disponibles: {list(self._scrapers)}")
        return self._scrapers[nombre]()

    def todos(self) -> list[BaseScraper]:
        return [cls() for cls in self._scrapers.values()]

    def nombres(self) -> list[str]:
        return list(self._scrapers.keys())


registry = ScraperRegistry()
