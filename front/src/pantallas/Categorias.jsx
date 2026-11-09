import { numero, obtenerCategorias } from "../api";
import { Cargando, ErrorCarga, Foto, usePeticion } from "../componentes";
import { enlaceCategoria } from "../enrutador";

export default function Categorias() {
  const { cargando, error, datos, reintentar } = usePeticion(() => obtenerCategorias(), []);

  const total = (datos || []).reduce((suma, c) => suma + c.productos, 0);

  return (
    <main className="contenedor ancho columna gap-16" aria-label="Categorías">
      <div className="columna gap-4">
        <h1 className="interior">Categorías</h1>
        <p className="secundario">
          {datos
            ? `${datos.length} categorías · ${numero(total)} productos. La barra muestra qué parte se puede comparar entre cadenas.`
            : "La barra muestra qué parte de cada categoría se puede comparar entre cadenas."}
        </p>
      </div>

      {cargando && <Cargando texto="Cargando las categorías…" tarjetas={6} />}
      {error && <ErrorCarga mensaje={error} reintentar={reintentar} />}

      {datos && (
        <div className="lista-categorias">
          {datos.map((c) => {
            const pct = c.productos ? Math.round((c.comparables / c.productos) * 100) : 0;
            return (
              <a key={c.nombre} href={enlaceCategoria(c.nombre)}>
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <Foto producto={{ imagen_url: c.imagen_url, nombre: c.nombre }} clase="chica" />
                  <div className="titulo" style={{ flex: 1 }}>
                    <strong>{c.nombre}</strong>
                    <span className="num secundario">{numero(c.productos)}</span>
                  </div>
                </div>
                <span className="barra-pista" aria-hidden="true">
                  <span style={{ width: `${pct}%` }} />
                </span>
                <span className="secundario">{numero(c.comparables)} comparables · {pct}%</span>
              </a>
            );
          })}
        </div>
      )}
    </main>
  );
}
