import asyncio, json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            locale="es-CL"
        )

        api_productos = []

        async def on_response(response):
            if response.status == 200:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    try:
                        d = await response.json()
                        # Buscar listas de productos en la respuesta
                        if isinstance(d, list) and len(d) > 0 and isinstance(d[0], dict):
                            for clave in ["productName", "name", "displayName"]:
                                if clave in d[0]:
                                    for p in d[:5]:
                                        nombre = p.get(clave, "")
                                        precio = None
                                        try:
                                            precio = p["items"][0]["sellers"][0]["commertialOffer"]["Price"]
                                        except Exception:
                                            precio = p.get("price") or p.get("offerPrice")
                                        ean = p.get("ean") or p.get("gtin")
                                        api_productos.append({"nombre": nombre, "precio": precio, "ean": ean, "url": response.url[:70]})
                                    break
                        elif isinstance(d, dict):
                            for k in ["products", "items", "data"]:
                                items = d.get(k)
                                if isinstance(items, list) and items:
                                    for p in items[:3]:
                                        api_productos.append({"nombre": p.get("name",""), "precio": p.get("price"), "url": response.url[:70]})
                                    break
                    except Exception:
                        pass

        page.on("response", on_response)

        await page.goto("https://www.jumbo.cl/busca/?ft=arroz", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(5000)

        print("=== APIS INTERCEPTADAS (Jumbo) ===")
        if api_productos:
            for p in api_productos[:6]:
                print(f"  [{p['url']}]")
                print(f"    nombre: {p['nombre']} | precio: {p['precio']} | ean: {p.get('ean')}")
        else:
            print("  Ninguna API interceptada con productos")

        # Inspeccionar clases del DOM
        clases = await page.evaluate("""() => {
            const all = document.querySelectorAll('*');
            const found = new Set();
            all.forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    el.className.split(' ').forEach(c => {
                        if (c && (c.includes('product') || c.includes('Product') ||
                                  c.includes('shelf') || c.includes('Shelf') ||
                                  c.includes('price') || c.includes('Price'))) {
                            found.add(c);
                        }
                    });
                }
            });
            return [...found].slice(0, 30);
        }""")
        print("\n=== CLASES DOM (Jumbo) ===")
        for c in clases:
            print(" ", c)

        # Screenshot
        await page.screenshot(path="debug_jumbo.png")
        print("\nScreenshot guardado: debug_jumbo.png")

        await browser.close()

asyncio.run(main())
