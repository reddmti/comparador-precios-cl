import { CADENAS, numero, obtenerCategorias, obtenerDestacados, recientes } from "../api";
import { Cargando, ErrorCarga, EstadoDeLosDatos, TarjetaProducto, usePeticion } from "../componentes";
import { enlaceBusqueda } from "../enrutador";
import { CANASTA } from "../medicion";

const EJEMPLOS = ["aceite de maravilla", "arroz grado 1", "leche entera", "detergente líquido"];

export default function Portada({ estado, dias, Buscador }) {
  const destacados = usePeticion(() => obtenerDestacados(6), []);
  const categorias = usePeticion(() => obtenerCategorias(), []);
  const previas = recientes();

  const comparables = (categorias.datos || []).reduce((suma, c) => suma + c.comparables, 0);

  return (
    <main className="contenedor ancho columna gap-40" aria-label="Portada">
      <section className="columna gap-16" style={{ maxWidth: 760 }}>
        <h1 className="portada">Compara precios de Jumbo, Santa Isabel y Unimarc.</h1>
        <p className="bajada">
          Escribe un producto y te mostramos en cuál de los tres está más barato hoy.
          Gratis, sin registro y sin instalar nada.
        </p>
        <Buscador grande />
        <div className="fila-chips">
          <span className="secundario">Prueba con:</span>
          {EJEMPLOS.map((e) => (
            <a key={e} className="chip" href={enlaceBusqueda(e)}>{e}</a>
          ))}
        </div>
        {previas.length > 0 && (
          <div className="fila-chips">
            <span className="secundario">Buscaste en este navegador:</span>
            {previas.map((e) => (
              <a key={e} className="chip gris" href={enlaceBusqueda(e)}>{e}</a>
            ))}
          </div>
        )}
      </section>

      <section className="bloque" aria-label="Cobertura y respaldo">
        <div className="fila-chips" style={{ gap: "10px 16px" }}>
          <span className="secundario" style={{ fontWeight: 600, color: "var(--text-medio)" }}>
            Comparamos
          </span>
          <div className="fila-chips">
            {CADENAS.map((c) => <span key={c} className="pill cadena">{c}</span>)}
          </div>
          <span className="secundario">Todavía no incluye Líder ni Tottus.</span>
        </div>

        <div className="estadisticas">
          <div>
            <span className="cifra">{numero(estado?.productos)}</span>
            <span className="secundario">productos con precio</span>
          </div>
          <div>
            <span className="cifra">{comparables ? numero(comparables) : "—"}</span>
            <span className="secundario">se pueden comparar en 2 o más cadenas</span>
          </div>
          <div>
            <span className="cifra">{(categorias.datos || []).length || "—"}</span>
            <span className="secundario">categorías de consumo habitual</span>
          </div>
          <EstadoDeLosDatos estado={estado} dias={dias} />
        </div>
      </section>

      <section className="bloque holgado" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px 24px", alignItems: "center" }}>
        <div className="columna gap-8">
          <h2>¿Vas a hacer la compra completa?</h2>
          <p className="medio">
            Pega tu lista, un producto por línea, y te decimos dónde sale más barata.
            Y qué conviene comprar en cada supermercado.
          </p>
          <a className="boton" href="#/lista" style={{ marginTop: 6 }}>Comparar mi lista</a>
        </div>
        <div className="columna gap-12" style={{ padding: 16, borderRadius: 10, background: "var(--bg)" }}>
          <span className="secundario" style={{ fontWeight: 600, color: "var(--text-medio)", fontSize: 13 }}>
            Lo que medimos en una canasta de {CANASTA.productos} productos
          </span>
          <BarraAhorro etiqueta="Ir solo a la cadena más barata" valor={CANASTA.elegirLaMasBarata} maximo={CANASTA.productoAProducto} />
          <BarraAhorro etiqueta="Comprar cada producto donde está más barato" valor={CANASTA.productoAProducto} maximo={CANASTA.productoAProducto} />
          <span className="secundario" style={{ fontSize: 13 }}>
            Ahorro frente a comprar todo en la cadena más cara.
          </span>
        </div>
      </section>

      <section className="columna gap-16">
        <div className="columna gap-4">
          <h2>Dónde más se gana hoy</h2>
          <p className="secundario">
            Los productos con más diferencia de precio entre cadenas, con el precio de hoy en cada una.
          </p>
        </div>
        {destacados.cargando && <Cargando texto="Buscando las mayores diferencias de hoy…" />}
        {destacados.error && <ErrorCarga mensaje={destacados.error} reintentar={destacados.reintentar} />}
        {destacados.datos && (
          <div className="grilla-productos">
            {destacados.datos.map((p) => <TarjetaProducto key={p.id} producto={p} />)}
          </div>
        )}
        <a className="boton secundario" href="#/categorias">Ver todas las categorías</a>
      </section>
    </main>
  );
}

function BarraAhorro({ etiqueta, valor, maximo }) {
  const ancho = `${Math.max(4, (valor / maximo) * 100)}%`;
  const texto = `${valor.toString().replace(".", ",")}%`;
  return (
    <div className="columna gap-4">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, fontSize: 14 }}>
        <span>{etiqueta}</span>
        <strong className="num" style={{ color: "var(--save)" }}>{texto}</strong>
      </div>
      <span className="barra-pista"><span style={{ width: ancho }} /></span>
    </div>
  );
}
