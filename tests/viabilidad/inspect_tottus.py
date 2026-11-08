import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            locale="es-CL",
            viewport={"width": 1280, "height": 800}
        )

        api_productos = []

        async def on_response(response):
            if response.status == 200:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    try:
                        d = await response.json()
                        # Buscar productos en la respuesta
                        listas = []
                        if isinstance(d, list):
                            listas = [d]
                        elif isinstance(d, dict):
                            for k in ["products", "items", "data", "results", "productSearch"]:
                                v = d.get(k)
                                if isinstance(v, list) and v:
                                    listas.append(v)
                                    break
                                elif isinstance(v, dict):
                                    for k2 in ["products", "items"]:
                                        v2 = v.get(k2)
                                        if isinstance(v2, list) and v2:
                                            listas.append(v2)
                                            break

                        for lista in listas:
                            if lista and isinstance(lista[0], dict):
                                nombre_key = next((k for k in ["productName", "name", "displayName", "title"] if k in lista[0]), None)
                                if nombre_key:
                                    for p in lista[:4]:
                                        nombre = p.get(nombre_key, "")
                                        precio = (p.get("price") or p.get("offerPrice") or
                                                  p.get("priceWithDiscount"))
                                        ean = p.get("ean") or p.get("gtin") or p.get("barcode")
                                        if nombre:
                                            api_productos.append({
                                                "nombre": nombre,
                                                "precio": precio,
                                                "ean": ean,
                                                "url": response.url[:80]
                                            })
                    except Exception:
                        pass

        page.on("response", on_response)

        await page.goto("https://www.tottus.cl/tottus/search?Ntt=arroz", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path="debug_tottus.png")

        print("=== APIs INTERCEPTADAS (Tottus) ===")
        for p in api_productos[:6]:
            print(f"  [{p['url']}]")
            print(f"    {p['nombre'][:60]} | ${p['precio']} | EAN: {p['ean']}")

        # Inspeccionar clases
        clases = await page.evaluate("""() => {
            const all = document.querySelectorAll('*');
            const found = new Set();
            all.forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    el.className.split(' ').forEach(c => {
                        if (c && (c.includes('product') || c.includes('Product') ||
                                  c.includes('price') || c.includes('Price') ||
                                  c.includes('shelf') || c.includes('Shelf'))) {
                            found.add(c);
                        }
                    });
                }
            });
            return [...found].slice(0, 25);
        }""")
        print("\n=== CLASES DOM (Tottus) ===")
        for c in clases:
            print(" ", c)

        # Intentar extraer con selectores comunes
        resultado = await page.evaluate("""() => {
            const selectores = [
                '[class*=product-card]', '[class*=ProductCard]', '[class*=productCard]',
                '[class*=product-name]', '[class*=ProductName]',
                '[class*=shelf]', 'article', '[data-testid*=product]'
            ];
            for (const sel of selectores) {
                const cards = document.querySelectorAll(sel);
                if (cards.length > 2) {
                    const ejemplos = [];
                    for (let i = 0; i < Math.min(3, cards.length); i++) {
                        const txt = cards[i].innerText.trim().replace(/\\n/g, ' | ').slice(0, 150);
                        if (txt.length > 5) ejemplos.push({sel, txt});
                    }
                    if (ejemplos.length) return ejemplos;
                }
            }
            return [{sel: 'none', txt: 'sin resultados'}];
        }""")
        print("\n=== PRODUCTOS DOM (Tottus) ===")
        for r in resultado:
            print(f"  [{r['sel']}] {r['txt']}")

        await browser.close()

asyncio.run(main())
