import asyncio
from playwright.async_api import async_playwright

async def probar_url(pw, url, nombre):
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        locale="es-CL",
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True  # ignorar SSL invalido para el test
    )
    api_hits = []
    async def on_response(r):
        if r.status == 200 and "json" in r.headers.get("content-type",""):
            try:
                d = await r.json()
                if isinstance(d, dict):
                    for k in ["products","items","data","results"]:
                        v = d.get(k)
                        if isinstance(v, list) and v and isinstance(v[0], dict):
                            api_hits.append({"url": r.url[:80], "count": len(v), "sample": v[0]})
                            break
            except:
                pass
    page.on("response", on_response)

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(4000)
        title = await page.title()
        body = await page.evaluate("() => document.body.innerText.slice(0,100)")
        await page.screenshot(path=f"debug_{nombre}.png")
        print(f"\n[{nombre}] titulo: {title}")
        print(f"  body: {body[:80]}")
        print(f"  APIs con productos: {len(api_hits)}")
        for h in api_hits[:3]:
            sample = h['sample']
            n = sample.get('name') or sample.get('displayName') or sample.get('productName','?')
            p = sample.get('price') or sample.get('offerPrice','?')
            print(f"    {h['url']} | {h['count']} items | ej: {n} ${p}")
    except Exception as e:
        print(f"\n[{nombre}] ERROR: {e}")
    finally:
        await browser.close()

async def main():
    urls = [
        ("https://tottus.falabella.com.cl/tottus-cl/search?Ntt=arroz", "tottus_falabella"),
        ("https://www.falabella.com/falabella-cl/search?Ntt=arroz&categ=cat40055",  "falabella_tottus"),
    ]
    async with async_playwright() as pw:
        for url, nombre in urls:
            await probar_url(pw, url, nombre)

asyncio.run(main())
