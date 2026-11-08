import asyncio
from playwright.async_api import async_playwright

TIENDAS = [
    ("Santa Isabel",   "https://www.santaisabel.cl/search?q=arroz"),
    ("Tottus",         "https://www.tottus.cl/tottus/search?Ntt=arroz"),
]

async def probar(pw, nombre, url):
    browser = await pw.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    ctx = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        locale="es-CL",
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True
    )
    await ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

    page = await ctx.new_page()
    productos_dom = []
    api_hits = []

    async def on_response(r):
        if r.status == 200 and "json" in r.headers.get("content-type",""):
            try:
                d = await r.json()
                listas = []
                if isinstance(d, list): listas = [d]
                elif isinstance(d, dict):
                    for k in ["products","items","data","results","availableProducts"]:
                        v = d.get(k)
                        if isinstance(v, list) and v: listas.append(v); break
                for lista in listas:
                    if lista and isinstance(lista[0], dict):
                        nk = next((k for k in ["name","displayName","productName"] if k in lista[0]), None)
                        if nk:
                            api_hits.append((r.url[:70], lista[:3], nk))
            except: pass
    page.on("response", on_response)

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=22000)
        await page.wait_for_timeout(5000)
        title = await page.title()
        body_preview = await page.evaluate("() => document.body.innerText.slice(0,80).replace(/\\n/g,' ')")

        # Detectar challenge
        is_blocked = any(x in title.lower() for x in ["robot","human","captcha","blocked","access denied"])

        # Buscar productos en DOM
        resultado = await page.evaluate("""() => {
            const sels = ['[class*=product-card]','[class*=ProductCard]','[class*=productCard]',
                          '[class*=shelf]','[class*=Shelf]','[class*=product-name]',
                          '[class*=nameProduct]','article'];
            for (const s of sels) {
                const els = document.querySelectorAll(s);
                if (els.length > 2) {
                    const txt = els[0].innerText.trim().replace(/\\n/g,' ').slice(0,100);
                    if (txt.length > 5) return {sel: s, count: els.length, sample: txt};
                }
            }
            return null;
        }""")

        await page.screenshot(path=f"debug_{nombre.replace(' ','_').lower()}.png")

        print(f"\n[{nombre}]")
        print(f"  URL: {url[:70]}")
        print(f"  Titulo: {title}")
        print(f"  Body: {body_preview}")
        print(f"  Bloqueado: {'SI (challenge)' if is_blocked else 'NO'}")
        if api_hits:
            print(f"  APIs con productos: {len(api_hits)}")
            for api_url, items, nk in api_hits[:2]:
                print(f"    {api_url}")
                for p in items[:2]:
                    print(f"      {p.get(nk,'')[:50]} | ${p.get('price') or p.get('offerPrice','?')}")
        if resultado:
            print(f"  DOM selector: {resultado['sel']} | {resultado['count']} elementos")
            print(f"  Muestra: {resultado['sample']}")
        elif not api_hits:
            print("  Sin datos en DOM ni API")

    except Exception as e:
        print(f"\n[{nombre}] ERROR: {e}")
    finally:
        await browser.close()

async def main():
    async with async_playwright() as pw:
        for nombre, url in TIENDAS:
            await probar(pw, nombre, url)

asyncio.run(main())
