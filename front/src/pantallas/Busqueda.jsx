import { numero, obtenerCategorias } from "../api";
import { usePeticion } from "../componentes";
import { enlaceBusqueda, enlaceCategoria } from "../enrutador";
import Listado from "./Listado";

export default function Busqueda({ termino, estado }) {
  const categorias = usePeticion(() => obtenerCategorias(), []);

  // Una palabra menos suele bastar: «aceite maravilla chef» no está, «aceite maravilla» sí.
  const palabras = termino.trim().split(/\s+/);
  const sugerencia = palabras.length > 1 ? palabras.slice(0, -1).join(" ") : null;

  return (
    <main className="contenedor angosto columna gap-16" aria-label="Resultados de búsqueda">
      <h1 className="interior">Resultados para «{termino}»</h1>

      <Listado
        q={termino}
        textoCargando={`Buscando «${termino}» en las tres cadenas…`}
        vacio={
          <div className="bloque">
            <h2>No encontramos nada para «{termino}»</h2>
            <p className="medio">
              Comparamos {numero(estado?.productos)} productos de Jumbo, Santa Isabel y
              Unimarc, y no todo está. Esto suele funcionar:
            </p>
            <ul className="medio columna gap-8" style={{ margin: 0, paddingLeft: 20 }}>
              {sugerencia && (
                <li>
                  Usa una palabra más general:{" "}
                  <a href={enlaceBusqueda(sugerencia)}>«{sugerencia}»</a> en vez de «{termino}».
                </li>
              )}
              <li>Quita la marca o el formato; los filtras después.</li>
              <li>Revisa la ortografía: «azúcar» y «azucar» funcionan igual.</li>
            </ul>
            {categorias.datos && (
              <div className="columna gap-8">
                <span className="secundario">O entra por categoría:</span>
                <div className="fila-chips">
                  {categorias.datos.slice(0, 10).map((c) => (
                    <a key={c.nombre} className="chip" href={enlaceCategoria(c.nombre)}>
                      {c.nombre} · {numero(c.productos)}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        }
      />

      <div className="bloque" style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
        <div className="columna gap-4">
          <strong>¿Tienes varios productos?</strong>
          <span className="secundario">Compara el costo total de tu lista en las tres cadenas.</span>
        </div>
        <a className="boton" href="#/lista">Compara tu lista completa →</a>
      </div>
    </main>
  );
}
