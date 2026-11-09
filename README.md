# Comparador de precios de supermercados

Obtiene los precios publicados por Jumbo, Santa Isabel y Unimarc, identifica qué
productos son equivalentes entre cadenas y expone la comparación mediante una API.

## Puesta en marcha

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

Sin configurar nada, el sistema guarda los datos en un archivo SQLite local
(`comparador.db`). Para usar PostgreSQL o Supabase, copia `.env.example` como `.env` y
completa `DATABASE_URL`; el mismo código funciona con ambos.

## Flujo completo

```bash
# 1. Obtener precios y cargarlos a la base, en un paso
python src/cargar.py --extraer arroz "leche entera" aceite detergente

# 2. Levantar la API
cd src && uvicorn api:app --reload --port 8000
```

La documentación interactiva queda en `http://localhost:8000/docs`.

Para cargar un archivo ya obtenido, en lugar de volver a consultar los sitios:

```bash
python src/cargar.py datos.json
```

## Endpoints

| Método | Ruta | Para qué sirve |
|---|---|---|
| GET | `/salud` | Estado del servicio y fecha de la última actualización |
| GET | `/categorias` | Categorías disponibles, con cuántos productos son comparables |
| GET | `/destacados?limite=6` | Productos donde hoy hay más diferencia entre cadenas |
| GET | `/buscar?q=arroz` | Busca productos y entrega su precio en cada cadena |
| GET | `/productos?categoria=arroz&orden=precio` | Listado paginado y ordenable, para categoría o búsqueda |
| GET | `/productos/{id}` | Detalle de un producto con sus precios vigentes |
| GET | `/productos/{id}/historial?dias=7` | Evolución del precio por cadena |
| POST | `/listas` | Costo total de una lista de compras por cadena |

Ejemplo de lista:

```json
{
  "sesion_id": "cualquier-identificador-del-cliente",
  "items": [
    { "texto": "aceite de maravilla miraflores 900 ml", "cantidad": 1 },
    { "texto": "azúcar blanca iansa 1 kg", "cantidad": 2 }
  ]
}
```

La respuesta separa tres grupos: los ítems comparables, que son los que tienen precio en
todas las cadenas y por lo tanto entran al total; los reconocidos pero sin precio en
alguna cadena; y los que no se pudieron reconocer. Los totales se calculan solo sobre el
primer grupo, porque de lo contrario se compararían canastas distintas y la cadena con
menos cobertura parecería la más barata.

## Interfaz web

```bash
cd front
npm install
cp .env.example .env     # VITE_API_URL apunta a la API
npm run dev              # http://localhost:5173
```

Son seis pantallas, enrutadas por fragmento (`#/ruta`) para que cualquier URL del
sitio se pueda recargar y compartir sin configurar reescrituras en el servidor:

| Ruta | Pantalla |
|---|---|
| `#/` | Portada: qué se compara, cobertura del día y dónde más se gana hoy |
| `#/categorias` | Las veinte categorías, con la proporción que se puede comparar |
| `#/categoria/arroz` | Listado de una categoría, con filtro y orden |
| `#/buscar?q=arroz` | Resultados de búsqueda, con la misma lista y controles |
| `#/producto/392` | Detalle: precio por cadena, precio por unidad, enlaces e historial |
| `#/lista` | Lista de compras: costo por cadena y qué conviene comprar en cada una |

No pide registro: la lista se asocia a un identificador anónimo que genera el propio
navegador, y lo que se escribe queda en `localStorage`.

El sistema visual está en `src/estilos.css`. Tres reglas de contenido que conviene no
romper al modificarlo: el verde nunca es el único portador de significado, porque donde
hay verde hay además un ✓ y la palabra «más barato»; la ausencia de dato se escribe
«sin información» y nunca $0 ni un guion; y una diferencia bajo el 5% se declara mínima
en lugar de celebrarla. Las cifras de la canasta que muestran la portada y la lista
salen de `src/medicion.js`, que es la medición del informe de E3 y no un texto suelto.

## Estructura

| Archivo | Responsabilidad |
|---|---|
| `src/engine.py` | Ejecuta los scrapers de las tres cadenas en paralelo |
| `src/scrapers/` | Un componente por cadena, más la lectura de precios compartida |
| `src/emparejar.py` | Normalización de nombres y decisión de equivalencia entre productos |
| `src/modelo.py` | Tablas y conexión a la base |
| `src/cargar.py` | Agrupa los productos obtenidos y registra el precio del día |
| `src/api.py` | API REST |
| `db/schema.sql` | Mismo esquema en SQL, para crearlo directamente en PostgreSQL |
| `front/` | Interfaz web en React + Vite |

## Pruebas

```bash
python -m pytest
```

Son 41 casos que no tocan la red: la lectura de precios con tarjetas reales de cada
cadena, las reglas de equivalencia, la carga a la base y los endpoints.

## Despliegue

El repositorio está en `github.com/reddmti/comparador-precios-cl` y la base de datos en
Supabase (PostgreSQL 17). La API y la interfaz se despliegan desde el mismo repositorio
como dos proyectos de Vercel distintos:

| Proyecto | Directorio raíz | Variable de entorno |
|---|---|---|
| API | `.` (usa `api/index.py` y `vercel.json`) | `DATABASE_URL` |
| Interfaz | `front` | `VITE_API_URL` |

La conexión a Supabase usa el *pooler* (`aws-0-us-east-1.pooler.supabase.com:5432`) y no
el host directo, porque este último solo resuelve en IPv6 y las funciones de Vercel
salen por IPv4. `crear_sesion()` usa `NullPool` y omite la creación de tablas cuando
detecta la variable `VERCEL`, de modo que cada invocación abra y cierre su conexión.

Para trasladar una base local ya poblada en lugar de volver a consultar los sitios:

```bash
python src/migrar.py          # de comparador.db a DATABASE_URL
```

Copia las tablas en orden de dependencia conservando los identificadores y, al terminar,
reajusta las secuencias de PostgreSQL.

### Actualización diaria

`.github/workflows/actualizar_precios.yml` obtiene las veinte consultas y registra el
precio del día a las 09:00 UTC. Necesita un solo secreto en el repositorio:

```bash
gh secret set DATABASE_URL --repo reddmti/comparador-precios-cl
```

También se puede lanzar a mano desde la pestaña Actions, indicando qué consultas
obtener.

## Qué falta

- Ampliar la cobertura de categorías: con las 20 obtenidas, 563 productos quedan
  comparables en dos o más cadenas y 147 en las tres.
- Acumular historial: hoy la base tiene un solo día de precios, así que el gráfico de
  evolución del detalle avisa que todavía no hay serie en lugar de dibujar una recta.
- Incorporar Líder y Tottus, que siguen sin implementar.
