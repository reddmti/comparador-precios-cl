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
| GET | `/buscar?q=arroz` | Busca productos y entrega su precio en cada cadena |
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

Tiene dos vistas: buscar un producto y ver su precio en cada cadena, y escribir una
lista de compras para obtener el costo total por cadena. No pide registro: la lista se
asocia a un identificador anónimo que genera el propio navegador.

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

Son 35 casos que no tocan la red: la lectura de precios con tarjetas reales de cada
cadena, las reglas de equivalencia, la carga a la base y los endpoints.

## Despliegue

Nada de esto está creado todavía. El orden que menos fricción genera es:

1. **Repositorio.** `git init`, commit y subir a GitHub. Los `.gitignore` ya excluyen
   `.env`, `node_modules/` y la base local.
2. **Base de datos.** Crear un proyecto en Supabase, copiar la cadena de conexión en
   `.env` como `DATABASE_URL` y ejecutar `python src/cargar.py datos.json` para
   poblarla. Las tablas se crean solas en la primera ejecución.
3. **API.** Desplegar en Railway apuntando a este repositorio, con `DATABASE_URL` como
   variable de entorno y el comando `uvicorn api:app --host 0.0.0.0 --port $PORT`
   ejecutado desde `src/`.
4. **Interfaz.** Desplegar `front/` en Vercel con `VITE_API_URL` apuntando a la URL de
   la API. Vercel reconoce Vite sin configuración adicional.
5. **Actualización diaria.** Una acción programada de GitHub que ejecute
   `python src/cargar.py --extraer <categorías>` una vez al día.

## Qué falta

- Crear las cuentas y desplegar según los pasos anteriores.
- Programar la obtención diaria.
- Ampliar la cobertura de categorías: con las 20 obtenidas, 547 productos quedan
  comparables en dos o más cadenas y 147 en las tres.
