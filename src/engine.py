"""
Motor de scraping. Carga todos los scrapers registrados y los ejecuta.

Para agregar una tienda nueva:
  1. Crear scrapers/nueva_tienda.py con clase que herede BaseScraper
  2. Decorarla con @registry.register("NombreTienda")
  3. Importarla aquí en _cargar_scrapers()
  Listo. El motor la descubre automáticamente.
"""

import asyncio
import importlib
from playwright.async_api import async_playwright
from scrapers.base import registry, Producto

SCRAPERS_DISPONIBLES = [
    "scrapers.jumbo",
    "scrapers.santa_isabel",
    "scrapers.unimarc",
    # Agregar nuevas tiendas aquí:
    # "scrapers.tottus",
    # "scrapers.lider",
]

def _cargar_scrapers():
    for modulo in SCRAPERS_DISPONIBLES:
        importlib.import_module(modulo)


async def scrape_todos(query: str, tiendas: list[str] | None = None) -> list[Producto]:
    """
    Ejecuta todos los scrapers registrados (o los de la lista `tiendas`) en paralelo.
    Retorna lista unificada de Producto.
    """
    _cargar_scrapers()

    scrapers = (
        [registry.get(t) for t in tiendas]
        if tiendas
        else registry.todos()
    )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

        async def _run_scraper(scraper):
            ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                ),
                locale="es-CL",
                viewport={"width": 1280, "height": 800},
            )
            await ctx.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )
            page = await ctx.new_page()
            try:
                productos = await scraper.scrape(page, query)
                # Normalizar: asegurarse que sean Producto aunque el scraper retorne dicts
                resultado = []
                for p in productos:
                    if isinstance(p, dict):
                        resultado.append(Producto(
                            nombre=p.get("nombre", ""),
                            precio=p.get("precio"),
                            tienda=p.get("tienda", scraper.nombre),
                            ean=p.get("ean"),
                            url=p.get("url"),
                            precio_por_kg=p.get("precio_por_kg"),
                            imagen_url=p.get("imagen_url"),
                        ))
                    else:
                        resultado.append(p)
                print(f"  [{scraper.nombre}] {len(resultado)} productos")
                return resultado
            except Exception as e:
                print(f"  [{scraper.nombre}] ERROR: {e}")
                return []
            finally:
                await ctx.close()

        # Ejecutar todos en paralelo
        resultados = await asyncio.gather(*[_run_scraper(s) for s in scrapers])
        await browser.close()

    todos = [p for lista in resultados for p in lista]
    return todos


if __name__ == "__main__":
    import json

    async def main():
        query = "arroz"
        print(f"\nBuscando: '{query}'")
        print(f"Tiendas registradas: {registry.nombres() if hasattr(registry, '_scrapers') else '(cargando...)'}")
        _cargar_scrapers()
        print(f"Tiendas cargadas: {registry.nombres()}\n")

        productos = await scrape_todos(query)

        print(f"\nTotal: {len(productos)} productos\n")
        for tienda in set(p.tienda for p in productos):
            grupo = [p for p in productos if p.tienda == tienda]
            print(f"  {tienda}: {len(grupo)} productos")
            for p in grupo[:3]:
                print(f"    {p.nombre[:55]} | ${p.precio}")

    asyncio.run(main())
