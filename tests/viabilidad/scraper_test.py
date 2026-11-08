#!/usr/bin/env python3
"""
Prueba de viabilidad: Scraping + Normalizacion de Productos
Comparador de Precios de Supermercados (Chile)

Testea:
  1. Si cada tienda responde sin necesidad de un navegador real (requests)
  2. Si se pueden extraer nombre, precio y EAN
  3. Si la normalizacion en capas puede emparejar el mismo producto entre tiendas

Uso:
  pip install -r requirements.txt
  python scraper_test.py
"""

import requests
import json
import re
import unicodedata
import time
from typing import Optional
from dataclasses import dataclass, field

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("[ERROR] Instalar: pip install beautifulsoup4")
    exit(1)

try:
    from rapidfuzz import fuzz
except ImportError:
    print("[ERROR] Instalar: pip install rapidfuzz")
    exit(1)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CL,es;q=0.9",
    "Accept": "application/json, text/html, */*",
}

QUERY = "arroz"  # producto de prueba — cambia esto para testear otros


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------

@dataclass
class Producto:
    nombre: str
    precio: Optional[float]
    ean: Optional[str]
    tienda: str
    url: Optional[str] = None
    # campos normalizados (se llenan en normalize())
    nombre_norm: str = ""
    peso_g: Optional[float] = None
    marca: str = ""

    def __str__(self):
        precio_str = f"${self.precio:,.0f}" if self.precio else "N/D"
        ean_str = self.ean if self.ean else "sin EAN"
        return f"  [{self.tienda}] {self.nombre} | {precio_str} | {ean_str}"


# ---------------------------------------------------------------------------
# Capa de normalizacion
# ---------------------------------------------------------------------------

UNIDADES = {
    r"(\d+(?:[.,]\d+)?)\s*kg\b": lambda v: float(v.replace(",", ".")) * 1000,
    r"(\d+(?:[.,]\d+)?)\s*g\b":  lambda v: float(v.replace(",", ".")),
    r"(\d+(?:[.,]\d+)?)\s*lt?\b": lambda v: float(v.replace(",", ".")) * 1000,
    r"(\d+(?:[.,]\d+)?)\s*ml\b": lambda v: float(v.replace(",", ".")),
    r"(\d+(?:[.,]\d+)?)\s*cc\b": lambda v: float(v.replace(",", ".")),
}

MARCAS_CONOCIDAS = [
    "tucapel", "luchetti", "carozzi", "colun", "soprole", "watts",
    "ideal", "costa", "nestea", "nescafe", "head & shoulders", "pantene",
    "dove", "savlon", "jumbo", "unimarc", "ekono",
]

def quitar_tildes(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")

def normalizar_texto(texto: str) -> str:
    texto = quitar_tildes(texto.lower().strip())
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto

def extraer_peso(texto: str) -> Optional[float]:
    texto_lower = texto.lower()
    for patron, convertir in UNIDADES.items():
        m = re.search(patron, texto_lower)
        if m:
            try:
                return convertir(m.group(1))
            except ValueError:
                pass
    return None

def extraer_marca(texto_norm: str) -> str:
    for marca in MARCAS_CONOCIDAS:
        if marca in texto_norm:
            return marca
    return ""

def normalize(producto: Producto) -> Producto:
    producto.nombre_norm = normalizar_texto(producto.nombre)
    producto.peso_g = extraer_peso(producto.nombre)
    producto.marca = extraer_marca(producto.nombre_norm)
    return producto


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def scrape_jumbo(query: str, limite: int = 6) -> list[Producto]:
    """
    Jumbo usa VTEX — tiene una API JSON publica sin autenticacion.
    Es el caso ideal: sin scraping de HTML, datos limpios.
    """
    print("\n[Jumbo] Consultando API VTEX...")
    url = "https://www.jumbo.cl/api/catalog_system/pub/products/search"
    params = {"ft": query, "_from": 0, "_to": limite - 1}

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=12)
        r.raise_for_status()
        datos = r.json()
    except requests.exceptions.HTTPError as e:
        print(f"  [!] HTTP {r.status_code} — posible bloqueo o cambio de API")
        return []
    except Exception as e:
        print(f"  [!] Error: {e}")
        return []

    productos = []
    for item in datos:
        nombre = item.get("productName", "")
        ean = item.get("ean") or ""

        precio = None
        try:
            precio = item["items"][0]["sellers"][0]["commertialOffer"]["Price"]
        except (KeyError, IndexError):
            pass

        link = f"https://www.jumbo.cl/{item.get('linkText', '')}/p"
        productos.append(Producto(nombre=nombre, precio=precio, ean=ean or None,
                                  tienda="Jumbo", url=link))

    print(f"  -> {len(productos)} productos encontrados")
    return productos


def scrape_lider(query: str, limite: int = 6) -> list[Producto]:
    """
    Lider (Walmart Chile). Intentamos con requests primero.
    Si la respuesta viene sin productos (JS requerido), lo reportamos.
    """
    print("\n[Lider] Consultando via requests...")
    url = f"https://www.lider.cl/supermercado/search"
    params = {"q": query}

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=12)
        r.raise_for_status()
    except Exception as e:
        print(f"  [!] Error: {e}")
        return []

    soup = BeautifulSoup(r.text, "lxml")

    # Intentar extraer datos estructurados (JSON-LD o script __NEXT_DATA__)
    next_data = soup.find("script", {"id": "__NEXT_DATA__"})
    if next_data:
        try:
            data = json.loads(next_data.string)
            productos_raw = (
                data.get("props", {})
                    .get("pageProps", {})
                    .get("initialData", {})
                    .get("searchResult", {})
                    .get("products", [])
            )
            productos = []
            for p in productos_raw[:limite]:
                nombre = p.get("displayName") or p.get("name", "")
                precio = p.get("price") or p.get("offerPrice")
                ean = p.get("ean") or p.get("gtin")
                productos.append(Producto(nombre=nombre, precio=precio,
                                          ean=ean, tienda="Lider"))
            print(f"  -> {len(productos)} productos via __NEXT_DATA__")
            return productos
        except Exception as e:
            print(f"  [!] __NEXT_DATA__ encontrado pero fallo el parse: {e}")

    # Fallback: buscar tarjetas de producto en HTML
    cards = soup.select("[data-testid='product-card'], .product-card, [class*='ProductCard']")
    if not cards:
        print("  [!] Sin resultados en HTML — el sitio probablemente requiere Playwright (JS)")
        print(f"      Status HTTP: {r.status_code} | Bytes recibidos: {len(r.content)}")
        return []

    productos = []
    for card in cards[:limite]:
        nombre_el = card.select_one("[class*='title'], [class*='name'], h3, h2")
        precio_el = card.select_one("[class*='price'], [class*='Price']")
        nombre = nombre_el.get_text(strip=True) if nombre_el else "?"
        precio_txt = precio_el.get_text(strip=True) if precio_el else ""
        precio = None
        m = re.search(r"[\d.,]+", precio_txt.replace(".", "").replace(",", ""))
        if m:
            try:
                precio = float(m.group())
            except ValueError:
                pass
        productos.append(Producto(nombre=nombre, precio=precio, ean=None, tienda="Lider"))

    print(f"  -> {len(productos)} productos via HTML")
    return productos


def scrape_unimarc(query: str, limite: int = 6) -> list[Producto]:
    """
    Unimarc. Mismo enfoque: requests -> __NEXT_DATA__ -> HTML -> reporte.
    """
    print("\n[Unimarc] Consultando via requests...")
    url = "https://www.unimarc.cl/search"
    params = {"q": query}

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=12)
        r.raise_for_status()
    except Exception as e:
        print(f"  [!] Error: {e}")
        return []

    soup = BeautifulSoup(r.text, "lxml")

    # Intentar __NEXT_DATA__
    next_data = soup.find("script", {"id": "__NEXT_DATA__"})
    if next_data:
        try:
            data = json.loads(next_data.string)
            # estructura puede variar, inspeccionamos las claves top-level
            claves = list(data.get("props", {}).get("pageProps", {}).keys())
            print(f"  -> __NEXT_DATA__ encontrado. Claves pageProps: {claves[:8]}")
            # intentar extraer productos de rutas comunes
            for ruta in ["products", "searchResult", "catalog", "items"]:
                candidato = data.get("props", {}).get("pageProps", {}).get(ruta)
                if isinstance(candidato, list) and candidato:
                    productos = []
                    for p in candidato[:limite]:
                        nombre = p.get("name") or p.get("displayName", "")
                        precio = p.get("price") or p.get("offerPrice")
                        ean = p.get("ean") or p.get("gtin")
                        productos.append(Producto(nombre=nombre, precio=precio,
                                                  ean=ean, tienda="Unimarc"))
                    print(f"  -> {len(productos)} productos via '{ruta}'")
                    return productos
        except Exception as e:
            print(f"  [!] Error parseando __NEXT_DATA__: {e}")

    # Fallback HTML
    cards = soup.select("[data-testid='product-card'], [class*='product'], article")
    if not cards:
        print("  [!] Sin resultados — probablemente requiere Playwright")
        print(f"      Status HTTP: {r.status_code} | Bytes: {len(r.content)}")
        return []

    productos = []
    for card in cards[:limite]:
        nombre_el = card.select_one("h2, h3, [class*='name'], [class*='title']")
        precio_el = card.select_one("[class*='price'], [class*='Price']")
        nombre = nombre_el.get_text(strip=True) if nombre_el else "?"
        precio_txt = precio_el.get_text(strip=True) if precio_el else ""
        precio = None
        m = re.search(r"\d+", precio_txt.replace(".", ""))
        if m:
            try:
                precio = float(m.group())
            except ValueError:
                pass
        productos.append(Producto(nombre=nombre, precio=precio, ean=None, tienda="Unimarc"))

    print(f"  -> {len(productos)} productos via HTML")
    return productos


# ---------------------------------------------------------------------------
# Motor de matching entre tiendas
# ---------------------------------------------------------------------------

def score_match(a: Producto, b: Producto) -> float:
    """
    Retorna un score 0-100 de que tan probable es que sean el mismo producto.
    Capa 1: EAN identico = 100
    Capa 2: mismo peso + marca + similitud de nombre >= 85 = score alto
    Capa 3: solo fuzzy sobre nombre normalizado
    """
    # Capa 1: EAN
    if a.ean and b.ean and a.ean == b.ean:
        return 100.0

    # Capa 2: peso + marca + nombre
    if a.peso_g and b.peso_g and abs(a.peso_g - b.peso_g) > 1:
        return 0.0  # distinto gramaje = distinto producto

    nombre_score = fuzz.token_sort_ratio(a.nombre_norm, b.nombre_norm)

    if a.marca and b.marca and a.marca != b.marca:
        return nombre_score * 0.3  # penaliza fuertemente si marcas distintas

    if a.peso_g and b.peso_g:
        return nombre_score  # mismo peso, confia mas en el fuzzy

    # Capa 3: solo fuzzy
    return nombre_score * 0.8  # descuento por falta de peso

UMBRAL_MATCH = 72.0

def encontrar_matches(lista_a: list[Producto], lista_b: list[Producto]) -> list[tuple]:
    matches = []
    for a in lista_a:
        for b in lista_b:
            score = score_match(a, b)
            if score >= UMBRAL_MATCH:
                matches.append((a, b, score))
    matches.sort(key=lambda x: -x[2])
    return matches


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print(f"  PRUEBA DE VIABILIDAD — query: '{QUERY}'")
    print("=" * 60)

    # 1. Scraping
    jumbo   = scrape_jumbo(QUERY)
    time.sleep(1)
    lider   = scrape_lider(QUERY)
    time.sleep(1)
    unimarc = scrape_unimarc(QUERY)

    todos = jumbo + lider + unimarc

    if not todos:
        print("\n[RESULTADO] Ningun sitio respondio con datos utilizables.")
        print("  -> Se necesita Playwright para todos. Viabilidad: MEDIA (requiere browser)")
        return

    # 2. Normalizacion
    print("\n" + "=" * 60)
    print("  PRODUCTOS ENCONTRADOS (pre-normalizacion)")
    print("=" * 60)
    for p in todos:
        print(p)

    todos_norm = [normalize(p) for p in todos]

    print("\n" + "=" * 60)
    print("  NORMALIZACION — nombre / peso / marca")
    print("=" * 60)
    for p in todos_norm:
        print(f"  [{p.tienda}] {p.nombre_norm[:60]} | peso: {p.peso_g}g | marca: '{p.marca}'")

    # 3. Matching entre tiendas
    pares = [
        ("Jumbo", "Lider",   [p for p in todos_norm if p.tienda == "Jumbo"],
                             [p for p in todos_norm if p.tienda == "Lider"]),
        ("Jumbo", "Unimarc", [p for p in todos_norm if p.tienda == "Jumbo"],
                             [p for p in todos_norm if p.tienda == "Unimarc"]),
        ("Lider", "Unimarc", [p for p in todos_norm if p.tienda == "Lider"],
                             [p for p in todos_norm if p.tienda == "Unimarc"]),
    ]

    print("\n" + "=" * 60)
    print(f"  MATCHES (umbral: {UMBRAL_MATCH})")
    print("=" * 60)
    total_matches = 0
    for nombre_a, nombre_b, lista_a, lista_b in pares:
        if not lista_a or not lista_b:
            continue
        matches = encontrar_matches(lista_a, lista_b)
        print(f"\n  {nombre_a} <-> {nombre_b}: {len(matches)} matches")
        for a, b, score in matches[:4]:
            metodo = "EAN" if (a.ean and b.ean and a.ean == b.ean) else "fuzzy"
            print(f"    [{score:.0f}% via {metodo}]")
            print(f"      {nombre_a}: {a.nombre} | ${a.precio}")
            print(f"      {nombre_b}: {b.nombre} | ${b.precio}")
        total_matches += len(matches)

    # 4. Resumen de viabilidad
    print("\n" + "=" * 60)
    print("  RESUMEN DE VIABILIDAD")
    print("=" * 60)
    tiendas_ok = [t for t in ["Jumbo", "Lider", "Unimarc"]
                  if any(p.tienda == t for p in todos)]
    tiendas_fail = [t for t in ["Jumbo", "Lider", "Unimarc"] if t not in tiendas_ok]

    print(f"  Tiendas con datos via requests : {tiendas_ok or 'ninguna'}")
    print(f"  Tiendas que necesitan Playwright: {tiendas_fail or 'ninguna'}")
    print(f"  Total productos obtenidos       : {len(todos)}")
    print(f"  Total matches encontrados       : {total_matches}")
    ean_count = sum(1 for p in todos if p.ean)
    print(f"  Productos con EAN               : {ean_count}/{len(todos)}")

    if not tiendas_fail:
        print("\n  -> VIABILIDAD ALTA: requests funciona en todos. Sin browser requerido.")
    elif len(tiendas_fail) == 1:
        print(f"\n  -> VIABILIDAD MEDIA-ALTA: solo {tiendas_fail[0]} requiere Playwright.")
    else:
        print("\n  -> VIABILIDAD MEDIA: requiere Playwright para scraping completo.")
        print("     Playwright es solucionable pero agrega complejidad al deploy.")

if __name__ == "__main__":
    main()
