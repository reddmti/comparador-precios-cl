import requests, json
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-CL",
}

r = requests.get("https://www.lider.cl/supermercado/search?q=arroz", headers=headers, timeout=15)
print(f"Status: {r.status_code} | Size: {len(r.content)/1024:.0f}KB")

soup = BeautifulSoup(r.text, "lxml")
tag = soup.find("script", {"id": "__NEXT_DATA__"})

if not tag:
    print("Sin __NEXT_DATA__")
    print("Primeros 300 chars:", r.text[:300])
else:
    print("__NEXT_DATA__ encontrado!")
    try:
        data = json.loads(tag.string)
        # Navegar estructura buscando productos
        props = data.get("props", {}).get("pageProps", {})
        print("Claves pageProps:", list(props.keys())[:10])

        # Buscar productos recursivamente
        def buscar_productos(obj, depth=0, path=""):
            if depth > 5:
                return []
            encontrados = []
            if isinstance(obj, list) and obj and isinstance(obj[0], dict):
                nombre_key = next((k for k in ["name","displayName","productName","title"] if k in obj[0]), None)
                precio_key = next((k for k in ["price","offerPrice","normalPrice","originalPrice"] if k in obj[0]), None)
                if nombre_key:
                    for p in obj[:5]:
                        encontrados.append({
                            "path": path,
                            "nombre": p.get(nombre_key,""),
                            "precio": p.get(precio_key) if precio_key else None,
                            "ean": p.get("ean") or p.get("gtin"),
                        })
                    return encontrados
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    sub = buscar_productos(v, depth+1, f"{path}.{k}")
                    if sub:
                        return sub
            return encontrados

        productos = buscar_productos(props)
        if productos:
            print(f"\n{len(productos)} productos encontrados:")
            for p in productos:
                print(f"  [{p['path']}] {p['nombre'][:60]} | ${p['precio']} | EAN:{p['ean']}")
        else:
            print("\nSin productos en __NEXT_DATA__. Guardando estructura...")
            with open("lider_nextdata.json", "w", encoding="utf-8") as f:
                json.dump(list(props.keys()), f, ensure_ascii=False, indent=2)
            print("Claves guardadas en lider_nextdata.json")
    except Exception as e:
        print(f"Error parseando: {e}")
