import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        # Intentar con slow_mo y args que hacen el browser menos detectable
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="es-CL",
            viewport={"width": 1366, "height": 768},
            java_script_enabled=True,
            # Simular timezone chilena
            timezone_id="America/Santiago",
        )

        # Ocultar que es Playwright
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        """)

        page = await context.new_page()

        api_productos = []
        async def on_response(response):
            if response.status == 200:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    try:
                        d = await response.json()
                        for k in ["products", "items", "data"]:
                            v = d.get(k) if isinstance(d, dict) else None
                            if isinstance(v, list) and v and isinstance(v[0], dict):
                                for p in v[:4]:
                                    n = p.get("displayName") or p.get("name", "")
                                    if n:
                                        api_productos.append({
                                            "nombre": n,
                                            "precio": p.get("price") or p.get("offerPrice"),
                                            "url": response.url[:80]
                                        })
                                break
                    except Exception:
                        pass
        page.on("response", on_response)

        print("[Lider v2] Probando con anti-deteccion...")
        await page.goto("https://www.lider.cl/supermercado/search?q=arroz", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(6000)
        await page.screenshot(path="debug_lider_v2.png")

        title = await page.title()
        print(f"  Titulo de pagina: {title}")

        if api_productos:
            print(f"  APIs interceptadas: {len(api_productos)}")
            for p in api_productos[:4]:
                print(f"    {p['nombre'][:60]} | ${p['precio']}")
        else:
            # Ver si sigue con el challenge DataDome
            body_text = await page.evaluate("() => document.body.innerText.slice(0, 200)")
            print(f"  Contenido pagina: {body_text[:200]}")

        await browser.close()

asyncio.run(main())
