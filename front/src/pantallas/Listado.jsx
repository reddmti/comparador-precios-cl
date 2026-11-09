import { useState } from "react";

import { listarProductos, numero } from "../api";
import { Cargando, ErrorCarga, TarjetaProducto, usePeticion } from "../componentes";

const ORDENES = [
  { clave: "diferencia", etiqueta: "Mayor diferencia" },
  { clave: "precio", etiqueta: "Menor precio" },
  { clave: "nombre", etiqueta: "Nombre" },
];

const POR_PAGINA = 24;

/**
 * Grilla con filtro, orden y «ver más», compartida por la pantalla de categoría y la
 * de resultados de búsqueda. Son la misma lista con distinto filtro, y separarlas en
 * dos componentes solo garantizaba que una se quedara atrás.
 */
export default function Listado({ categoria, q, textoCargando, vacio, mostrarRecuento = true }) {
  const [orden, setOrden] = useState("diferencia");
  const [soloComparables, setSoloComparables] = useState(false);
  const [pagina, setPagina] = useState(0);

  const limite = POR_PAGINA * (pagina + 1);
  const { cargando, error, datos, reintentar } = usePeticion(
    () => listarProductos({ categoria, q, orden, soloComparables, limite, desde: 0 }),
    [categoria, q, orden, soloComparables, limite],
  );

  const cambiar = (accion) => { accion(); setPagina(0); };

  return (
    <>
      {/* Sin resultados no hay nada que ordenar ni filtrar: los controles solo
          aparecen si hay lista, o si fue el propio filtro el que la dejó vacía. */}
      <div className="fila-chips" style={{ justifyContent: "space-between" }}
           hidden={Boolean(datos) && datos.items.length === 0 && !soloComparables}>
        <div className="fila-chips" role="group" aria-label="Filtrar">
          <button type="button" className="chip" aria-pressed={!soloComparables}
                  onClick={() => cambiar(() => setSoloComparables(false))}>
            Todos
          </button>
          <button type="button" className="chip" aria-pressed={soloComparables}
                  onClick={() => cambiar(() => setSoloComparables(true))}>
            Solo comparables
          </button>
        </div>
        <div className="fila-chips">
          <span className="secundario" id="etiqueta-orden">Ordenar</span>
          <div className="fila-chips" role="group" aria-labelledby="etiqueta-orden">
            {ORDENES.map((o) => (
              <button key={o.clave} type="button" className="chip" aria-pressed={orden === o.clave}
                      onClick={() => cambiar(() => setOrden(o.clave))}>
                {o.etiqueta}
              </button>
            ))}
          </div>
        </div>
      </div>

      {cargando && !datos && <Cargando texto={textoCargando} />}
      {error && <ErrorCarga mensaje={error} termino={q} reintentar={reintentar} />}

      {datos && datos.items.length === 0 && vacio}

      {datos && datos.items.length > 0 && (
        <>
          {/* La pantalla de categoría ya informa el total en su encabezado; aquí solo
              se repite cuando el filtro lo cambia, para no decir dos veces lo mismo. */}
          {(mostrarRecuento || soloComparables) && (
            <p className="secundario" role="status">
              {soloComparables
                ? `${numero(datos.total)} productos con precio en dos o más cadenas`
                : `${numero(datos.total)} productos · ${numero(datos.comparables)} se pueden comparar`}
            </p>
          )}
          <div className="grilla-productos">
            {datos.items.map((p) => <TarjetaProducto key={p.id} producto={p} />)}
          </div>
          {datos.items.length < datos.total && (
            <button type="button" className="boton secundario" style={{ alignSelf: "center" }}
                    disabled={cargando} onClick={() => setPagina((n) => n + 1)}>
              {cargando ? "Cargando…" : `Ver más (${numero(datos.total - datos.items.length)} restantes)`}
            </button>
          )}
        </>
      )}
    </>
  );
}
