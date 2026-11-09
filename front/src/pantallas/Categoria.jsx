import { numero, obtenerCategorias } from "../api";
import { Migas, usePeticion } from "../componentes";
import { enlaceCategoria } from "../enrutador";
import Listado from "./Listado";

export default function Categoria({ nombre }) {
  const { datos } = usePeticion(() => obtenerCategorias(), []);
  const ficha = (datos || []).find((c) => c.nombre === nombre);
  const pct = ficha && ficha.productos
    ? Math.round((ficha.comparables / ficha.productos) * 100)
    : null;

  return (
    <main className="contenedor angosto columna gap-16" aria-label={`Categoría ${nombre}`}>
      <Migas pasos={[
        { texto: "Inicio", href: "#/" },
        { texto: "Categorías", href: "#/categorias" },
        { texto: nombre },
      ]} />

      <div className="columna gap-4">
        <h1 className="interior" style={{ textTransform: "capitalize" }}>{nombre}</h1>
        {ficha && (
          <p className="secundario">
            {numero(ficha.productos)} productos · {numero(ficha.comparables)} se pueden
            comparar entre cadenas ({pct}%)
          </p>
        )}
      </div>

      <Listado
        categoria={nombre}
        mostrarRecuento={false}
        textoCargando={`Cargando precios de ${nombre}…`}
        vacio={
          <div className="bloque">
            <h2>No hay productos en esta categoría</h2>
            <p className="medio">
              Puede que la última actualización no haya alcanzado a registrarla.
              Prueba con <a href="#/categorias">otra categoría</a>.
            </p>
          </div>
        }
      />

      {datos && (
        <section className="columna gap-8" style={{ marginTop: 16 }}>
          <h2>Otras categorías</h2>
          <div className="fila-chips">
            {datos.filter((c) => c.nombre !== nombre).slice(0, 12).map((c) => (
              <a key={c.nombre} className="chip" href={enlaceCategoria(c.nombre)}>
                {c.nombre} · {numero(c.productos)}
              </a>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
