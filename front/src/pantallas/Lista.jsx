import { useEffect, useState } from "react";

import { CADENAS, compararLista, numero, pesos } from "../api";
import { enlaceBusqueda, enlaceProducto } from "../enrutador";
import { CANASTA } from "../medicion";

const CLAVE = "comparador_lista";
const EJEMPLO = "aceite de maravilla miraflores 900 ml\nleche colun entera 1 l\nnescafe tradicion 170 g";

export default function Lista() {
  const [texto, setTexto] = useState(() => localStorage.getItem(CLAVE) ?? EJEMPLO);
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => { localStorage.setItem(CLAVE, texto); }, [texto]);

  const lineas = texto.split("\n").map((l) => l.trim()).filter((l) => l.length > 1);

  async function comparar(evento) {
    evento.preventDefault();
    if (lineas.length === 0) return;
    setCargando(true);
    setError(null);
    try {
      setResultado(await compararLista(lineas.map((l) => ({ texto: l, cantidad: 1 }))));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <main className="contenedor angosto columna gap-20" aria-label="Lista de compras">
      <div className="columna gap-8">
        <h1 className="interior">Lista de compras</h1>
        <p className="bajada">
          Escribe o pega tu lista, un producto por línea. Te decimos cuánto sale en cada
          cadena y qué conviene comprar en cada una.
        </p>
      </div>

      <form className="bloque" onSubmit={comparar}>
        <div className="columna gap-4">
          <label htmlFor="lista" style={{ fontWeight: 600 }}>Tu lista</label>
          <span className="secundario">
            {lineas.length} {lineas.length === 1 ? "producto" : "productos"} · se guarda
            solo en este navegador
          </span>
        </div>
        <textarea id="lista" value={texto} onChange={(e) => setTexto(e.target.value)} />
        <button type="submit" className="boton" disabled={cargando || lineas.length === 0}>
          {cargando ? "Comparando…" : "Comparar mi lista"}
        </button>
      </form>

      {error && (
        <div role="alert" className="aviso">
          <span aria-hidden="true" className="signo">!</span>
          <div className="cuerpo">
            <strong>No pudimos comparar tu lista</strong>
            <span className="secundario medio">Tu lista sigue escrita. Vuelve a intentarlo. ({error})</span>
          </div>
        </div>
      )}

      {resultado && <Resultado datos={resultado} />}
    </main>
  );
}

function Resultado({ datos }) {
  const entran = datos.items.filter((i) => i.entra_al_total);
  const fuera = datos.items.filter((i) => i.producto && !i.entra_al_total);
  const sinReconocer = datos.items.filter((i) => !i.producto);
  const masCara = datos.totales[datos.totales.length - 1];
  const masBarata = datos.totales[0];

  return (
    <>
      <section className="columna gap-12">
        <h2>Reconocimos tu lista así</h2>
        <div className="recuento">
          <div>
            <strong className="cifra">{entran.length}</strong>
            <span className="secundario" style={{ fontWeight: 600, color: "var(--text-medio)" }}>
              {entran.length === 1 ? "entra al total" : "entran al total"}
            </span>
            <span className="secundario">Tienen precio en todas las cadenas.</span>
          </div>
          <div>
            <strong className="cifra">{fuera.length}</strong>
            <span className="secundario" style={{ fontWeight: 600, color: "var(--text-medio)" }}>
              {fuera.length === 1 ? "queda fuera" : "quedan fuera"}
            </span>
            <span className="secundario">
              {fuera.length ? "Los reconocimos, pero falta el precio en alguna cadena." : "Todo lo reconocido está en las tres."}
            </span>
          </div>
          <div>
            <strong className="cifra">{sinReconocer.length}</strong>
            <span className="secundario" style={{ fontWeight: 600, color: "var(--text-medio)" }}>sin reconocer</span>
            <span className="secundario">
              {sinReconocer.length ? "No encontramos un producto que corresponda." : "Todo lo que escribiste lo encontramos."}
            </span>
          </div>
        </div>

        {fuera.length > 0 && entran.length > 0 && (
          <div className="bloque">
            <strong>
              Por qué el total suma solo {entran.length} de tus {datos.items.length} productos
            </strong>
            <p className="medio">
              Para comparar, las tres canastas tienen que tener lo mismo.{" "}
              {fuera[0].producto?.nombre} no tiene precio en {fuera[0].cadenas_que_faltan.join(" ni ") || "alguna cadena"}:
              si lo sumáramos en las demás, esa cadena parecería más barata solo porque su
              canasta tiene un producto menos.
            </p>
          </div>
        )}
      </section>

      {datos.totales.length > 0 && (
        <>
          <section className="columna gap-12">
            <h2>Dónde compro todo</h2>
            <div className="bloque">
              <div className="columna gap-4">
                <span className="marbarato">✓ Lo mejor es ir solo a {datos.cadena_recomendada}</span>
                <span className="precio-ganador detalle">{pesos(masBarata.total)}</span>
              </div>
              <div className="columna gap-8">
                {datos.totales.map((t) => (
                  <div key={t.cadena} className={`fila-cadena${t.cadena === datos.cadena_recomendada ? " mejor" : ""}`}>
                    <span className="nombre">
                      {t.cadena === datos.cadena_recomendada ? `✓ ${t.cadena}` : t.cadena}
                    </span>
                    <span className="barra" aria-hidden="true">
                      <span style={{ width: `${(t.total / masCara.total) * 100}%` }} />
                    </span>
                    <span className="valor">{pesos(t.total)}</span>
                  </div>
                ))}
              </div>
              <span className="secundario">
                {datos.items_comparables === 1
                  ? "Total del único producto que está en las tres cadenas."
                  : `Total de los ${datos.items_comparables} productos que están en las tres cadenas.`}
              </span>
            </div>
          </section>

          <section className="columna gap-12">
            <h2>Qué compro en cada lado</h2>
            <div className="bloque">
              <div className="columna gap-4">
                <span className="marbarato">✓ Cada producto donde está más barato</span>
                <span className="precio-ganador detalle">{pesos(datos.total_optimo)}</span>
              </div>
              <div className="columna gap-8">
                {entran.map((item, i) => {
                  const p = item.producto;
                  const mejor = p.precios.find((x) => x.precio === p.menor_precio);
                  return (
                    <div key={`${i}-${item.texto}`} className="fila-cadena">
                      <span className="nombre" style={{ gridColumn: "1 / 3", paddingLeft: 0 }}>
                        <a href={enlaceProducto(p.id)}>{p.nombre}</a>{" "}
                        <span className="marbarato">✓ en {mejor?.cadena}</span>
                      </span>
                      <span className="valor">{pesos(p.menor_precio)}</span>
                    </div>
                  );
                })}
              </div>
              {/* Con un solo producto comparable, repartir la compra es ir a la cadena
                  más barata: la frase de ahorro diría «$0 menos» y sobra. */}
              <span className="secundario">
                {datos.optimo_vs_mas_barata > 0
                  ? `${pesos(datos.optimo_vs_mas_barata)} menos que comprar todo en ${masBarata.cadena}, y ${pesos(datos.optimo_vs_mas_cara)} menos que todo en ${masCara.cadena}.`
                  : `Con esta lista, repartir la compra no mejora lo que ya consigues yendo solo a ${masBarata.cadena}. Agrega más productos y la diferencia suele aparecer.`}
              </span>
            </div>
          </section>

          <section className="bloque">
            <h2>En una compra grande, la diferencia crece</h2>
            <p className="medio">
              Lo medimos en una canasta de {CANASTA.productos} productos con precio en las
              tres cadenas, contra comprar todo en la más cara.
            </p>
            <div className="columna gap-12">
              <Barra etiqueta="Elegir la cadena más barata y comprar todo ahí"
                     valor={CANASTA.elegirLaMasBarata} maximo={CANASTA.productoAProducto} />
              <Barra etiqueta="Comprar cada producto donde está más barato"
                     valor={CANASTA.productoAProducto} maximo={CANASTA.productoAProducto} />
            </div>
            <span className="secundario">
              Ninguna cadena es la más barata en todo. El ahorro está en repartir la compra.
            </span>
          </section>
        </>
      )}

      {entran.length > 0 && (
        <Grupo titulo={`Entran al total · ${entran.length}`} items={entran} />
      )}
      {fuera.length > 0 && (
        <Grupo titulo={`Reconocidos, fuera del total · ${fuera.length}`} items={fuera} />
      )}
      {sinReconocer.length > 0 && (
        <section className="columna gap-12">
          <h2>Sin reconocer · {sinReconocer.length}</h2>
          <p className="medio">
            No encontramos un producto que corresponda con certeza. Preferimos no adivinar:
            un emparejamiento equivocado te daría un precio que no es. Busca estas líneas a
            mano y agrégalas con el nombre que usa la tienda.
          </p>
          <div className="fila-chips">
            {sinReconocer.map((item, i) => (
              <a key={`${i}-${item.texto}`} className="chip" href={enlaceBusqueda(item.texto)}>
                Buscar «{item.texto}»
              </a>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

function Grupo({ titulo, items }) {
  return (
    <section className="columna gap-12">
      <h2>{titulo}</h2>
      {items.map((item, i) => {
        const p = item.producto;
        return (
          <article key={`${i}-${item.texto}`} className="grupo-item">
            <span className="secundario">Escribiste «{item.texto}»</span>
            <div className="encabezado-meta">
              <a href={enlaceProducto(p.id)} style={{ fontWeight: 600 }}>{p.nombre}</a>
              {p.formato && <span className="pill formato">{p.formato}</span>}
            </div>
            <div className="columna gap-4">
              {CADENAS.map((cadena) => {
                const dato = p.precios.find((x) => x.cadena === cadena);
                if (!dato) {
                  return (
                    <span key={cadena} className="secundario">
                      {cadena}: <span className="sin-info">sin información</span>
                    </span>
                  );
                }
                const esMenor = dato.precio === p.menor_precio && p.precios.length > 1;
                return (
                  <span key={cadena} className="secundario num"
                        style={esMenor ? { color: "var(--save)", fontWeight: 700 } : undefined}>
                    {esMenor ? "✓ " : ""}{cadena} {pesos(dato.precio)}
                  </span>
                );
              })}
            </div>
            {item.cadenas_que_faltan.length > 0 && (
              <span className="secundario">
                Fuera del total porque falta el precio en {item.cadenas_que_faltan.join(" y ")}.
              </span>
            )}
          </article>
        );
      })}
    </section>
  );
}

function Barra({ etiqueta, valor, maximo }) {
  return (
    <div className="columna gap-4">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, fontSize: 14 }}>
        <span>{etiqueta}</span>
        <strong className="num" style={{ color: "var(--save)" }}>
          {valor.toString().replace(".", ",")}%
        </strong>
      </div>
      <span className="barra-pista"><span style={{ width: `${Math.max(4, (valor / maximo) * 100)}%` }} /></span>
    </div>
  );
}
