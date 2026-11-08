import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            locale="es-CL"
        )
        # Santa Isabel es Cencosud — misma plataforma que Jumbo
        await page.goto("https://www.santaisabel.cl/busca/?ft=arroz", wait_until="domcontentloaded", timeout=22000)
        await page.wait_for_timeout(4000)

        productos = await page.evaluate("""() => {
            const nombres = document.querySelectorAll('.product-card-name');
            const precios = document.querySelectorAll('.ppum-price-container');
            const result = [];
            nombres.forEach((el, i) => {
                result.push({
                    nombre: el.innerText.trim(),
                    precio: precios[i] ? precios[i].innerText.split('\\n')[0].trim() : 'N/D'
                });
            });
            return result.slice(0, 6);
        }""")

        title = await page.title()
        print(f"Titulo: {title}")
        print(f"Productos encontrados: {len(productos)}")
        for p in productos:
            print(f"  {p['nombre'][:60]} | {p['precio']}")

        await page.screenshot(path="debug_santa_isabel2.png")
        await browser.close()

asyncio.run(main())
