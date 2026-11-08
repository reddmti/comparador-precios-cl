import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            locale="es-CL"
        )

        # Interceptar llamadas a la API interna de Unimarc
        api_data = []
        async def on_response(response):
            if response.status == 200 and ("search" in response.url or "product" in response.url):
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    try:
                        d = await response.json()
                        api_data.append({"url": response.url[:80], "data": d})
                    except Exception:
                        pass
        page.on("response", on_response)

        await page.goto("https://www.unimarc.cl/search?q=arroz", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(5000)

        # Extraer productos con las clases descubiertas
        productos = await page.evaluate("""() => {
            const nombres = document.querySelectorAll('[class*=nameProduct]');
            const marcas  = document.querySelectorAll('[class*=brandText]');
            const result  = [];
            nombres.forEach((el, i) => {
                result.push({
                    nombre: el.innerText.trim(),
                    marca: marcas[i] ? marcas[i].innerText.trim() : ''
                });
            });
            return result.slice(0, 8);
        }""")

        print("=== PRODUCTOS UNIMARC ===")
        for p in productos:
            print(f"  {p['marca']} | {p['nombre']}")

        # Buscar precios - clases comunes en sitios VTEX/Next
        precios = await page.evaluate("""() => {
            const candidatos = [
                '[class*=price]', '[class*=Price]', '[class*=precio]',
                '[class*=Precio]', '[class*=offerPrice]'
            ];
            for (const sel of candidatos) {
                const els = document.querySelectorAll(sel);
                if (els.length > 2) {
                    const vals = [];
                    els.forEach(el => {
                        const t = el.innerText.trim();
                        if (t && t.includes('$')) vals.push(t.replace(/\\n/g,' '));
                    });
                    if (vals.length > 0) return {selector: sel, valores: vals.slice(0, 10)};
                }
            }
            return {selector: 'none', valores: []};
        }""")
        print(f"\n=== PRECIOS (selector: {precios['selector']}) ===")
        for v in precios['valores']:
            print(f"  {v}")

        # Mostrar APIs interceptadas
        print(f"\n=== APIs INTERCEPTADAS ({len(api_data)}) ===")
        for item in api_data[:5]:
            print(f"  {item['url']}")
            d = item['data']
            if isinstance(d, dict):
                print(f"    claves: {list(d.keys())[:6]}")

        await browser.close()

asyncio.run(main())
