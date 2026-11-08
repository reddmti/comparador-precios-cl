import { useEffect, useState } from "react";
import { buscarProductos, compararLista, obtenerEstado, pesos } from "./api";

const CADENAS = ["Jumbo", "Santa Isabel", "Unimarc"];

export default function App() {
  const [vista, setVista] = useState("buscar");
  const [estado, setEstado] = useState(null);

  useEffect(() => {
    obtenerEstado().then(setEstado).catch(() => setEstado({ estado: "sin conexión" }));
  }, []);

  return (
    <div className="pagina">
      <header>
        <h1>Comparador de precios de supermercados</h1>
        <p className="bajada">
          Compara el precio de un producto entre Jumbo, Santa Isabel y Unimarc, o el
          costo total de tu lista de compras.
        </p>
        <nav>
          <button className={vista === "buscar" ? "activo" : ""} onClick={() => setVista("buscar")}>
            Buscar un producto
          </button>
          <button className={vista === "lista" ? "activo" : ""} onClick={() => setVista("lista")}>
            Mi lista de compras
          </button>
        </nav>
      </header>

      <main>{vista === "buscar" ? <Buscador /> : <ListaDeCompras />}</main>

      <footer>
        {estado?.ultima_actualizacion ? (
          <>
            {estado.productos.toLocaleString("es-CL")} productos · precios actualizados al{" "}
            {new Date(estado.ultima_actualizacion + "T00:00:00").toLocaleDateString("es-CL")}
          </>
        ) : (
          "Sin conexión con el servicio de precios"
        )}
      </footer>
    </div>
  );
}

function Buscador() {
  const [consulta, setConsulta] = useState("");
  const [resultados, setResultados] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  async function buscar(evento) {
    evento.preventDefault();
    if (consulta.trim().length < 2) return;
    setCargando(true);
    setError(null);
    try {
      setResultados(await buscarProductos(consulta.trim()));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <section>
      <form onSubmit={buscar} className="buscador">
        <input
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
          placeholder="Por ejemplo: aceite de maravilla, arroz grado 1, leche entera"
          aria-label="Producto a buscar"
        />
        <button type="submit" disabled={cargando}>
          {cargando ? "Buscando…" : "Comparar"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {resultados?.length === 0 && <p className="vacio">No se encontraron productos para esa búsqueda.</p>}

      {resultados?.map((producto) => (
        <TarjetaProducto key={producto.id} producto={producto} />
      ))}
    </section>
  );
}

function TarjetaProducto({ producto }) {
  const porCadena = Object.fromEntries(producto.precios.map((p) => [p.cadena, p]));
  const menor = producto.menor_precio;

  return (
    <article className="producto">
      <div className="producto-encabezado">
        <h2>{producto.nombre}</h2>
        <div className="meta">
          {producto.formato && <span className="formato">{producto.formato}</span>}
          {producto.ahorro > 0 && (
            <span className="ahorro">Diferencia de {pesos(producto.ahorro)}</span>
          )}
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Cadena</th>
            <th>Precio</th>
            <th>Producto en la tienda</th>
          </tr>
        </thead>
        <tbody>
          {CADENAS.map((cadena) => {
            const dato = porCadena[cadena];
            if (!dato) {
              return (
                <tr key={cadena} className="sin-dato">
                  <td>{cadena}</td>
                  <td colSpan={2}>Sin información</td>
                </tr>
              );
            }
            return (
              <tr key={cadena} className={dato.precio === menor ? "mejor" : ""}>
                <td>{cadena}</td>
                <td className="precio">
                  {pesos(dato.precio)}
                  {dato.precio === menor && <span className="etiqueta">menor precio</span>}
                </td>
                <td>
                  {dato.url ? (
                    <a href={dato.url} target="_blank" rel="noreferrer">
                      {dato.nombre_en_cadena}
                    </a>
                  ) : (
                    dato.nombre_en_cadena
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </article>
  );
}

function ListaDeCompras() {
  const [texto, setTexto] = useState(
    "aceite de maravilla miraflores 900 ml\nazúcar blanca iansa 1 kg\nleche colun entera 1 l",
  );
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  async function comparar(evento) {
    evento.preventDefault();
    const items = texto
      .split("\n")
      .map((linea) => linea.trim())
      .filter((linea) => linea.length > 1)
      .map((linea) => ({ texto: linea, cantidad: 1 }));
    if (items.length === 0) return;

    setCargando(true);
    setError(null);
    try {
      setResultado(await compararLista(items));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <section>
      <form onSubmit={comparar} className="lista">
        <label htmlFor="items">Escribe un producto por línea</label>
        <textarea
          id="items"
          rows={8}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
        <button type="submit" disabled={cargando}>
          {cargando ? "Calculando…" : "Calcular el costo por cadena"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {resultado && (
        <div className="resultado-lista">
          <h2>Costo de tu lista</h2>
          <p className="nota">
            El total considera los {resultado.items_comparables} productos que tienen
            precio en las tres cadenas, para que la comparación sea entre canastas iguales.
          </p>

          <table>
            <thead>
              <tr>
                <th>Cadena</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {resultado.totales.map((total) => (
                <tr key={total.cadena} className={total.cadena === resultado.cadena_recomendada ? "mejor" : ""}>
                  <td>{total.cadena}</td>
                  <td className="precio">
                    {pesos(total.total)}
                    {total.cadena === resultado.cadena_recomendada && (
                      <span className="etiqueta">conviene aquí</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {resultado.ahorro_vs_mas_cara > 0 && (
            <p className="destacado">
              Comprando en {resultado.cadena_recomendada} ahorras{" "}
              {pesos(resultado.ahorro_vs_mas_cara)} respecto de la cadena más cara.
            </p>
          )}

          {resultado.items_sin_comparacion.length > 0 && (
            <div className="aviso">
              <strong>Fuera del total</strong>
              <ul>
                {resultado.items_sin_comparacion.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {resultado.items_no_reconocidos.length > 0 && (
            <div className="aviso">
              <strong>No se reconocieron</strong>
              <ul>
                {resultado.items_no_reconocidos.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p className="nota">
                Prueba escribiendo la marca y el formato, por ejemplo «arroz tucapel 1 kg».
              </p>
            </div>
          )}

          {resultado.items_reconocidos.map((producto) => (
            <TarjetaProducto key={producto.id} producto={producto} />
          ))}
        </div>
      )}
    </section>
  );
}
