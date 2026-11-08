"""
Intenta encontrar la API móvil de Lider (Walmart Chile).
Las apps móviles suelen tener endpoints distintos al web, sin DataDome.
"""
import requests, json

HEADERS_MOBILE = {
    "User-Agent": "okhttp/4.9.2",  # Android app User-Agent
    "Accept": "application/json",
    "Accept-Language": "es-CL",
}

HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 Chrome/112.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json",
    "x-requested-with": "com.walmartchile.lider",
}

candidatos = [
    ("https://bff.lider.cl/api/search?q=arroz&limit=5", HEADERS_MOBILE),
    ("https://api.lider.cl/search?q=arroz&limit=5", HEADERS_MOBILE),
    ("https://www.lider.cl/api/search?q=arroz", HEADERS_WEB),
    ("https://www.lider.cl/supermercado/api/search?query=arroz", HEADERS_WEB),
    ("https://apigw.lider.cl/api/v1/search?q=arroz", HEADERS_MOBILE),
    ("https://bff-gateway.lider.cl/search?q=arroz", HEADERS_MOBILE),
]

print("=== TEST API MOVIL LIDER ===")
for url, headers in candidatos:
    try:
        r = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        ct = r.headers.get("content-type","")
        print(f"\n{r.status_code} | {len(r.content)}b | {url[:70]}")
        if r.status_code == 200 and "json" in ct:
            d = r.json()
            print(f"  -> JSON! Claves: {list(d.keys())[:6]}")
        elif r.status_code not in [404, 403, 410]:
            print(f"  -> {r.text[:100]}")
    except Exception as e:
        print(f"\nERROR: {e} | {url[:60]}")
