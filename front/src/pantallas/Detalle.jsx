import { CADENAS, fechaCorta, fechaLarga, leerProducto, obtenerHistorial, obtenerProducto, pesos } from "../api";
import { Cargando, ErrorCarga, FilaCadena, Foto, Migas, usePeticion } from "../componentes";
import { enlaceCategoria } from "../enrutador";

const COLORES = { Jumbo: "#1d4ed8", "Santa Isabel": "#c2410c", Unimarc: "#15803d" };

export default function Detalle({ id }) {
  const { cargando, error, datos, reintentar } = usePeticion(() => obtenerProducto(id), [id]);

  if (cargando) {
    return (
      <main className="contenedor angosto columna gap-16">
        <Cargando texto="Cargando el producto…" tarjetas={1} />
      </main>
    );
  }
  if (error) {
    return (
      <main className="contenedor angosto columna gap-16">
        <ErrorCarga mensaje={error} reintentar={reintentar} />
      </main>
    );
  }

  const p = leerProducto(datos);
  const fecha = p.precios[0]?.fecha;

  return (
    <main className="contenedor angosto columna gap-20" aria-label="Detalle de producto">
      <Migas pasos={[
        { texto: "Inicio", href: "#/" },
        { texto: p.categoria, href: enlaceCategoria(p.categoria) },
      ]} />

      <div className="columna gap-8">
        <h1 className="interior">{p.nombre}</h1>
        <div className="encabezado-meta">
          {p.formato && <span className="pill formato">{p.formato}</span>}
          <span className="secundario">
            {p.cobertura}{fecha ? ` · precios del ${fechaLarga(fecha)}` : ""}
          </span>
        </div>
      </div>

      <section className="bloque" style={{ display: "grid", gridTemplateColumns: "minmax(0, 220px) minmax(0, 1fr)", gap: 24, alignItems: "start" }}>
        <Foto producto={p} clase="grande" />
        {p.comparable ? (
          <div className="columna gap-12">
            <div className="columna" style={{ gap: 2 }}>
              <span className="marbarato">✓ Más barato en {p.cadena_mas_barata}</span>
              <span className="precio-ganador detalle">{pesos(p.menor_precio)}</span>
            </div>
            <span className={`pill ${p.minima ? "minima" : "ahorro"}`} style={{ alignSelf: "flex-start" }}>
              {p.diferencia}
            </span>
            <div role="list" className="filas-cadena">
              {p.filas.map((fila) => <FilaCadena key={fila.cadena} fila={fila} />)}
            </div>
          </div>
        ) : (
          <div className="columna gap-8">
            <span className="secundario medio" style={{ fontWeight: 600 }}>
              Solo en {p.cadena_mas_barata} · no se puede comparar
            </span>
            <span className="precio-ganador solo detalle">{pesos(p.menor_precio)}</span>
            <p className="secundario">
              Las otras cadenas no publican este producto, o no pudimos asociarlo con el suyo.
            </p>
          </div>
        )}
      </section>

      <section className="columna gap-12">
        <h2>Precio en cada cadena</h2>
        {CADENAS.map((cadena) => {
          const dato = p.porCadena[cadena];
          if (!dato) {
            return (
              <article key={cadena} className="bloque-cadena">
                <div className="linea">
                  <strong>{cadena}</strong>
                  <span className="sin-info">sin información</span>
                </div>
                <span className="secundario">
                  {cadena} no publica este producto en su sitio, o no lo pudimos asociar
                  con el de las otras cadenas.
                </span>
              </article>
            );
          }
          const esMenor = p.comparable && dato.precio === p.menor_precio;
          return (
            <article key={cadena} className={`bloque-cadena${esMenor ? " mejor" : ""}`}>
              <div className="linea">
                <strong>{esMenor ? `✓ ${cadena} · Más barato` : cadena}</strong>
                <span className="precio">{pesos(dato.precio)}</span>
              </div>
              <div className="linea">
                <span className="secundario">
                  En la tienda: «{dato.nombre_en_cadena}» · dato del {fechaLarga(dato.fecha)}
                </span>
                {dato.precio_por_unidad != null && (
                  <span className="secundario num">{pesos(dato.precio_por_unidad)} por unidad de medida</span>
                )}
              </div>
              {dato.url && (
                <a href={dato.url} target="_blank" rel="noreferrer" style={{ fontSize: 14, fontWeight: 600 }}>
                  Ver en {cadena} ↗
                </a>
              )}
            </article>
          );
        })}
      </section>

      <PorUnidad producto={p} />

      <Historial id={id} />

      <p className="secundario">
        El precio y el nombre son los que publica cada cadena en su sitio para cualquier
        visitante. Antes de decidir, revisa el enlace: en tienda puede ser distinto.
      </p>
    </main>
  );
}

/**
 * Comparación por unidad de medida.
 *
 * Es el dato que más veces cambia la decisión y el que menos se mira: la cadena con el
 * precio más bajo no siempre es la que sale más barata por kilo o por litro, porque los
 * envases difieren. Solo se muestra cuando las tres cifras existen y no son todas
 * iguales; si no, el bloque no aporta nada y estorba.
 */
function PorUnidad({ producto }) {
  const con = producto.precios.filter((x) => x.precio_por_unidad != null);
  if (con.length < 2) return null;

  const valores = con.map((x) => x.precio_por_unidad);
  const menor = Math.min(...valores);
  const mayor = Math.max(...valores);
  if (menor === mayor) return null;

  const baratoUnidad = con.find((x) => x.precio_por_unidad === menor);
  const difiere = baratoUnidad.cadena !== producto.cadena_mas_barata;

  return (
    <section className="columna gap-12">
      <h2>Precio por unidad de medida</h2>
      <div className="bloque" style={{ gap: 12 }}>
        <div role="list" className="filas-cadena">
          {con.sort((a, b) => a.precio_por_unidad - b.precio_por_unidad).map((x) => (
            <div key={x.cadena} role="listitem"
                 className={`fila-cadena${x.precio_por_unidad === menor ? " mejor" : ""}`}>
              <span className="nombre">
                {x.precio_por_unidad === menor ? `✓ ${x.cadena}` : x.cadena}
              </span>
              <span className="barra" aria-hidden="true">
                <span style={{ width: `${(x.precio_por_unidad / mayor) * 100}%` }} />
              </span>
              <span className="valor">{pesos(x.precio_por_unidad)}</span>
            </div>
          ))}
        </div>
        <p className="secundario">
          {difiere
            ? `Ojo: el precio más bajo está en ${producto.cadena_mas_barata}, pero por unidad de medida conviene ${baratoUnidad.cadena}. El envase no es del mismo tamaño en las dos.`
            : `${baratoUnidad.cadena} es la más barata tanto en precio como por unidad de medida.`}
        </p>
      </div>
    </section>
  );
}

function Historial({ id }) {
  const { cargando, datos } = usePeticion(() => obtenerHistorial(id, 30), [id]);
  if (cargando || !datos) return null;

  const series = datos.series || {};
  const fechas = [...new Set(Object.values(series).flat().map((d) => d.fecha))].sort();

  return (
    <section className="columna gap-12">
      <h2>Cómo ha cambiado el precio</h2>
      {fechas.length < 2 ? (
        <p className="medio">
          Todavía no hay historial: estos precios son del primer registro guardado para
          este producto. La actualización diaria va acumulando la serie, y aquí aparecerá
          la evolución en cuanto haya dos días distintos.
        </p>
      ) : (
        <>
          <Grafico series={series} fechas={fechas} />
          <table>
            <caption className="solo-lectores">Precio de hoy, mínimo y máximo de los últimos 30 días</caption>
            <thead>
              <tr>
                <th>Cadena</th><th className="num">Hoy</th><th className="num">Mínimo</th><th className="num">Máximo</th>
              </tr>
            </thead>
            <tbody>
              {CADENAS.filter((c) => series[c]?.length).map((c) => {
                const valores = series[c].map((d) => d.precio);
                return (
                  <tr key={c}>
                    <td>{c}</td>
                    <td className="num">{pesos(valores[valores.length - 1])}</td>
                    <td className="num">{pesos(Math.min(...valores))}</td>
                    <td className="num">{pesos(Math.max(...valores))}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

/** Gráfico de líneas mínimo, en SVG: una dependencia menos y escala con el texto. */
function Grafico({ series, fechas }) {
  const ancho = 820, alto = 220, margen = { arriba: 12, derecha: 12, abajo: 28, izquierda: 64 };
  const valores = Object.values(series).flat().map((d) => d.precio);
  const min = Math.min(...valores), max = Math.max(...valores);
  const rango = max - min || 1;

  const x = (fecha) => margen.izquierda
    + (fechas.indexOf(fecha) / Math.max(1, fechas.length - 1))
      * (ancho - margen.izquierda - margen.derecha);
  const y = (precio) => margen.arriba
    + (1 - (precio - min) / rango) * (alto - margen.arriba - margen.abajo);

  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${ancho} ${alto}`} role="img" width="100%"
           aria-label={`Evolución del precio entre el ${fechas[0]} y el ${fechas[fechas.length - 1]}`}>
        <line x1={margen.izquierda} y1={alto - margen.abajo} x2={ancho - margen.derecha}
              y2={alto - margen.abajo} stroke="var(--borde)" />
        <text x={8} y={y(max) + 4} fontSize="12" fill="var(--muted)">{pesos(max)}</text>
        <text x={8} y={y(min) + 4} fontSize="12" fill="var(--muted)">{pesos(min)}</text>
        {fechas.map((f) => (
          <text key={f} x={x(f)} y={alto - 8} fontSize="12" fill="var(--muted)" textAnchor="middle">
            {fechaCorta(f)}
          </text>
        ))}
        {Object.entries(series).map(([cadena, puntos]) => (
          <polyline key={cadena} fill="none" strokeWidth="2" stroke={COLORES[cadena] || "var(--neutro)"}
                    points={puntos.map((d) => `${x(d.fecha)},${y(d.precio)}`).join(" ")} />
        ))}
      </svg>
      <figcaption className="fila-chips secundario" style={{ marginTop: 8 }}>
        {Object.keys(series).map((cadena) => (
          <span key={cadena} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span aria-hidden="true" style={{ width: 14, height: 3, background: COLORES[cadena] || "var(--neutro)", display: "inline-block" }} />
            {cadena}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
