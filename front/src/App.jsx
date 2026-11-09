import { useEffect, useState } from "react";

import { buscarSugerencias, diasDesde, fechaLarga, obtenerEstado, recordarBusqueda } from "./api";
import { enlaceBusqueda, enlaceProducto, ir, useRuta, useSubirAlInicio } from "./enrutador";
import Busqueda from "./pantallas/Busqueda";
import Categoria from "./pantallas/Categoria";
import Categorias from "./pantallas/Categorias";
import Detalle from "./pantallas/Detalle";
import Lista from "./pantallas/Lista";
import Portada from "./pantallas/Portada";

export default function App() {
  const { vista, partes, parametros } = useRuta();
  const [estado, setEstado] = useState(null);

  useEffect(() => {
    obtenerEstado().then(setEstado).catch(() => setEstado(null));
  }, []);

  useSubirAlInicio(`${vista}/${partes[1] || ""}/${parametros.q || ""}`);

  const dias = diasDesde(estado?.ultima_actualizacion);
  const enPortada = vista === "portada";

  return (
    <div className="pagina">
      <header className="cabecera">
        <div className="contenedor ancho">
          <a className="marca" href="#/">
            <span className="punto" aria-hidden="true" />
            SuperCompara
          </a>
          <nav className="navegacion" aria-label="Principal">
            <a href="#/categorias" aria-current={vista === "categorias" || vista === "categoria" ? "page" : undefined}>
              Categorías
            </a>
            <a href="#/lista" aria-current={vista === "lista" ? "page" : undefined}>
              Lista de compras
            </a>
          </nav>
          {!enPortada && <Buscador valorInicial={parametros.q || ""} />}
        </div>
      </header>

      {vista === "portada" && <Portada estado={estado} dias={dias} Buscador={Buscador} />}
      {vista === "categorias" && <Categorias />}
      {vista === "categoria" && <Categoria nombre={partes[1] || ""} />}
      {vista === "buscar" && <Busqueda termino={parametros.q || ""} estado={estado} />}
      {vista === "producto" && <Detalle id={partes[1]} />}
      {vista === "lista" && <Lista />}
      {!["portada", "categorias", "categoria", "buscar", "producto", "lista"].includes(vista) && (
        <main className="contenedor angosto columna gap-16">
          <h1 className="interior">Esa página no existe</h1>
          <p className="medio">
            Puede que el enlace esté incompleto. Vuelve a la <a href="#/">portada</a> o
            revisa las <a href="#/categorias">categorías</a>.
          </p>
        </main>
      )}

      <footer className="pie">
        <div className="contenedor ancho">
          <span>
            {estado
              ? `${estado.productos.toLocaleString("es-CL")} productos de Jumbo, Santa Isabel y Unimarc · precios del ${fechaLarga(estado.ultima_actualizacion)}`
              : "Sin conexión con el servicio de precios"}
          </span>
          <span>
            Los precios son los que cada cadena publica en su sitio. Antes de comprar,
            revisa el enlace del producto: en tienda pueden ser distintos. Sin registro
            y sin datos personales.
          </span>
        </div>
      </footer>
    </div>
  );
}

function Buscador({ grande, valorInicial = "" }) {
  const [consulta, setConsulta] = useState(valorInicial);
  const [sugerencias, setSugerencias] = useState([]);
  const [abierto, setAbierto] = useState(false);
  const [marcado, setMarcado] = useState(-1);

  // Al llegar a la pantalla de resultados por un enlace, el campo muestra lo buscado.
  useEffect(() => { setConsulta(valorInicial); }, [valorInicial]);

  // Se espera a que la persona deje de escribir antes de preguntar: sin esto, «leche»
  // dispara cinco consultas y las respuestas pueden llegar desordenadas.
  useEffect(() => {
    const termino = consulta.trim();
    if (termino.length < 2 || termino === valorInicial) { setSugerencias([]); return; }
    let vigente = true;
    const id = setTimeout(() => {
      buscarSugerencias(termino)
        .then((datos) => { if (vigente) { setSugerencias(datos); setMarcado(-1); } })
        .catch(() => { if (vigente) setSugerencias([]); });
    }, 180);
    return () => { vigente = false; clearTimeout(id); };
  }, [consulta, valorInicial]);

  function buscar(termino) {
    const limpio = termino.trim();
    if (limpio.length < 2) return;
    recordarBusqueda(limpio);
    setAbierto(false);
    ir(enlaceBusqueda(limpio).slice(1));
  }

  function enviar(evento) {
    evento.preventDefault();
    if (abierto && marcado >= 0 && sugerencias[marcado]) {
      setAbierto(false);
      ir(enlaceProducto(sugerencias[marcado].producto_id).slice(1));
      return;
    }
    buscar(consulta);
  }

  function teclas(evento) {
    if (!abierto || sugerencias.length === 0) return;
    if (evento.key === "ArrowDown") {
      evento.preventDefault();
      setMarcado((n) => (n + 1) % sugerencias.length);
    } else if (evento.key === "ArrowUp") {
      evento.preventDefault();
      setMarcado((n) => (n <= 0 ? sugerencias.length : n) - 1);
    } else if (evento.key === "Escape") {
      setAbierto(false);
    }
  }

  const visibles = abierto && sugerencias.length > 0;

  return (
    <form role="search" className={`buscador${grande ? " grande" : ""}`} onSubmit={enviar}>
      <div className="campo-busqueda">
        <label style={{ flex: 1, display: "flex" }}>
          <span className="solo-lectores">Buscar producto</span>
          <input
            type="search"
            value={consulta}
            onChange={(e) => { setConsulta(e.target.value); setAbierto(true); }}
            onFocus={() => setAbierto(true)}
            onBlur={() => setTimeout(() => setAbierto(false), 150)}
            onKeyDown={teclas}
            role="combobox"
            aria-expanded={visibles}
            aria-controls="lista-sugerencias"
            aria-autocomplete="list"
            autoComplete="off"
            placeholder={grande
              ? "Ej.: aceite de maravilla, arroz grado 1"
              : "Busca un producto, ej.: arroz grado 1"}
          />
        </label>
        {visibles && (
          <ul className="sugerencias" id="lista-sugerencias" role="listbox">
            {sugerencias.map((s, i) => (
              <li key={s.producto_id} role="option" aria-selected={i === marcado}>
                <button type="button" aria-selected={i === marcado}
                        onMouseEnter={() => setMarcado(i)}
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => { setAbierto(false); ir(enlaceProducto(s.producto_id).slice(1)); }}>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {s.nombre}
                  </span>
                  <span className="donde">
                    {s.cadenas > 1 ? `${s.cadenas} cadenas` : "1 cadena"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <button type="submit">Buscar</button>
    </form>
  );
}
