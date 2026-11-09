import { useEffect, useState } from "react";

import { diasDesde, fechaLarga, obtenerEstado, recordarBusqueda } from "./api";
import { enlaceBusqueda, ir, useRuta, useSubirAlInicio } from "./enrutador";
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

  // Al llegar a la pantalla de resultados por un enlace, el campo muestra lo buscado.
  useEffect(() => { setConsulta(valorInicial); }, [valorInicial]);

  function enviar(evento) {
    evento.preventDefault();
    const termino = consulta.trim();
    if (termino.length < 2) return;
    recordarBusqueda(termino);
    ir(enlaceBusqueda(termino).slice(1));
  }

  return (
    <form role="search" className={`buscador${grande ? " grande" : ""}`} onSubmit={enviar}>
      <label>
        <span className="solo-lectores">Buscar producto</span>
        <input
          type="search"
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
          placeholder={grande
            ? "Ej.: aceite de maravilla, arroz grado 1"
            : "Busca un producto, ej.: arroz grado 1"}
        />
      </label>
      <button type="submit">Buscar</button>
    </form>
  );
}
