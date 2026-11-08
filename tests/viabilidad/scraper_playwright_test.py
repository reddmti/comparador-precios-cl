#!/usr/bin/env python3
"""
Prueba de viabilidad con Playwright (navegador real headless).
Testea Jumbo, Lider y Unimarc con un navegador Chromium.

Uso:
  pip install playwright
  playwright install chromium
  python scraper_playwright_test.py
"""

import json
import re
import asyncio
import unicodedata
from dataclasses import dataclass
from typing import Optional

from playwright.async_api import async_playwright

QUERY = "arroz"
LIMITE = 5


@dataclass
class Producto:
    nombre: str
    precio: Optional[float]
    ean: Optional[str]
    tienda: str


# ---------------------------------------------------------------------------
# Normalizacion (identica al script anterior)
# ---------------------------------------------------------------------------

def quitar_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn")

def normalizar(t):
    t = quitar_tildes(t.lower().strip())
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t)

def extraer_peso(t):
    patrones = [
        (r"(\d+[.,]?\d*)\s*kg\b", 1000),
        (r"(\d+[.,]?\d*)\s*g\b",  1),
        (r"(\d+[.,]?\d*)\s*lt?\b", 1000),
        (r"(\d+[.,]?\d*)\s*ml\b", 1),
    ]
    for patron, factor in patrones:
        m = re.search(patron, t.lower())
        if m:
            try:
                return float(m.group(1).replace(",", ".")) * factor
            except ValueError:
                pass
    return None


# ---------------------------------------------------------------------------
# Scrapers Playwright
# ---------------------------------------------------------------------------

async def scrape_jumbo_pw(page, query: str) -> list[Producto]:
    print("\n[Jumbo] Navegando con Playwright...")
    url = f"https://www.jumbo.cl/{query}"

    # Interceptar respuestas de la API interna mientras carga la pagina
    productos_api = []

    async def on_response(response):
        if "product_search" in response.url or "intelligent-search" in response.url:
            try:
                data = await response.json()
                for p in data.get("products", [])[:LIMITE]:
                    nombre = p.get("productName") or p.get("name", "")
                    ean = p.get("ean")
                    precio = None
                    try:
                        precio = p["items"][0]["sellers"][0]["commertialOffer"]["Price"]
                    except (KeyError, IndexError):
                        pass
                    productos_api.append(Producto(nombre, precio, ean, "Jumbo"))
                    print(f"  [API] {nombre} | ${precio} | EAN:{ean}")
            except Exception:
                pass

    page.on("response", on_response)

    try:
        await page.goto(url, wait_until="networkidle", timeout=20000)
    except Exception:
        pass

    if productos_api:
        print(f"  -> {len(productos_api)} productos via intercepcion de API")
        return productos_api

    # Fallback: extraer del DOM
    await page.wait_for_timeout(3000)
    cards = await page.query_selector_all("[class*='product'], [class*='Product'], article")
    productos = []
    for card in cards[:LIMITE]:
        nombre_el = await card.query_selector("h2, h3, [class*='name'], [class*='title']")
        precio_el = await card.query_selector("[class*='price'], [class*='Price']")
        nombre = (await nombre_el.inner_text()).strip() if nombre_el else "?"
        precio_txt = (await precio_el.inner_text()).strip() if precio_el else ""
        precio = None
        m = re.search(r"\d[\d.]*", precio_txt.replace(".", ""))
        if m:
            try:
                precio = float(m.group().replace(".", ""))
            except ValueError:
                pass
        productos.append(Producto(nombre, precio, None, "Jumbo"))

    print(f"  -> {len(productos)} productos via DOM")
    return productos


async def scrape_lider_pw(page, query: str) -> list[Producto]:
    print("\n[Lider] Navegando con Playwright...")
    url = f"https://www.lider.cl/supermercado/search?q={query}"

    productos_api = []

    async def on_response(response):
        url_r = response.url
        if ("search" in url_r or "product" in url_r) and "api" in url_r:
            try:
                data = await response.json()
                items = (data.get("products") or data.get("items")
                         or data.get("data", {}).get("products", []))
                for p in (items or [])[:LIMITE]:
                    nombre = p.get("displayName") or p.get("name", "")
                    precio = p.get("price") or p.get("offerPrice")
                    ean = p.get("ean") or p.get("gtin")
                    if nombre:
                        productos_api.append(Producto(nombre, precio, ean, "Lider"))
                        print(f"  [API] {nombre} | ${precio}")
            except Exception:
                pass

    page.on("response", on_response)

    try:
        await page.goto(url, wait_until="networkidle", timeout=20000)
    except Exception:
        pass

    if productos_api:
        print(f"  -> {len(productos_api)} productos via intercepcion de API")
        return productos_api

    # Fallback DOM
    await page.wait_for_timeout(3000)
    cards = await page.query_selector_all("[data-testid='product-card'], [class*='ProductCard'], [class*='product-card']")
    productos = []
    for card in cards[:LIMITE]:
        nombre_el = await card.query_selector("h2, h3, [class*='name']")
        precio_el = await card.query_selector("[class*='price'], [class*='Price']")
        nombre = (await nombre_el.inner_text()).strip() if nombre_el else "?"
        precio_txt = (await precio_el.inner_text()).strip() if precio_el else ""
        precio = None
        m = re.search(r"\d[\d.]*", precio_txt.replace(".", ""))
        if m:
            try:
                precio = float(m.group())
            except ValueError:
                pass
        productos.append(Producto(nombre, precio, None, "Lider"))

    # Si DOM tampoco tiene nada, tomar screenshot para debug
    if not productos:
        await page.screenshot(path="debug_lider.png")
        print("  [!] Sin resultados. Screenshot guardado: debug_lider.png")
    else:
        print(f"  -> {len(productos)} productos via DOM")

    return productos


async def scrape_unimarc_pw(page, query: str) -> list[Producto]:
    print("\n[Unimarc] Navegando con Playwright...")
    url = f"https://www.unimarc.cl/search?q={query}"

    productos_api = []

    async def on_response(response):
        if "search" in response.url and response.status == 200:
            try:
                data = await response.json()
                for key in ["products", "items", "results"]:
                    items = data.get(key, [])
                    if items:
                        for p in items[:LIMITE]:
                            nombre = p.get("name") or p.get("displayName", "")
                            precio = p.get("price") or p.get("offerPrice")
                            ean = p.get("ean") or p.get("gtin")
                            if nombre:
                                productos_api.append(Producto(nombre, precio, ean, "Unimarc"))
                                print(f"  [API] {nombre} | ${precio}")
                        break
            except Exception:
                pass

    page.on("response", on_response)

    try:
        await page.goto(url, wait_until="networkidle", timeout=20000)
    except Exception:
        pass

    if productos_api:
        print(f"  -> {len(productos_api)} productos via intercepcion de API")
        return productos_api

    await page.wait_for_timeout(3000)
    cards = await page.query_selector_all("[class*='product'], article, [class*='card']")
    productos = []
    for card in cards[:LIMITE]:
        nombre_el = await card.query_selector("h2, h3, [class*='name'], [class*='title']")
        precio_el = await card.query_selector("[class*='price']")
        nombre = (await nombre_el.inner_text()).strip() if nombre_el else "?"
        if nombre and nombre != "?":
            precio_txt = (await precio_el.inner_text()).strip() if precio_el else ""
            precio = None
            m = re.search(r"\d[\d.]*", precio_txt.replace(".", ""))
            if m:
                try:
                    precio = float(m.group())
                except ValueError:
                    pass
            productos.append(Producto(nombre, precio, None, "Unimarc"))

    if not productos:
        await page.screenshot(path="debug_unimarc.png")
        print("  [!] Sin resultados. Screenshot guardado: debug_unimarc.png")
    else:
        print(f"  -> {len(productos)} productos via DOM")

    return productos


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print(f"  PRUEBA PLAYWRIGHT — query: '{QUERY}'")
    print("=" * 60)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="es-CL",
            viewport={"width": 1280, "height": 800},
        )

        jumbo   = await scrape_jumbo_pw(await context.new_page(), QUERY)
        lider   = await scrape_lider_pw(await context.new_page(), QUERY)
        unimarc = await scrape_unimarc_pw(await context.new_page(), QUERY)

        await browser.close()

    todos = jumbo + lider + unimarc

    print("\n" + "=" * 60)
    print("  PRODUCTOS ENCONTRADOS")
    print("=" * 60)
    for p in todos:
        precio_str = f"${p.precio:,.0f}" if p.precio else "N/D"
        print(f"  [{p.tienda}] {p.nombre[:55]} | {precio_str}")

    print("\n" + "=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    for tienda in ["Jumbo", "Lider", "Unimarc"]:
        n = sum(1 for p in todos if p.tienda == tienda)
        eans = sum(1 for p in todos if p.tienda == tienda and p.ean)
        print(f"  {tienda}: {n} productos | {eans} con EAN")

    print()
    if len(todos) >= 6:
        print("  -> VIABILIDAD CONFIRMADA con Playwright.")
    elif len(todos) > 0:
        print(f"  -> VIABILIDAD PARCIAL: {len(todos)} productos. Ajustar selectores CSS.")
    else:
        print("  -> Sin datos. Revisar screenshots de debug.")


if __name__ == "__main__":
    asyncio.run(main())
