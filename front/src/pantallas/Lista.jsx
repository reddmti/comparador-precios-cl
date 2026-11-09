import { useEffect, useRef, useState } from "react";

import { CADENAS, compararLista, numero, pesos } from "../api";
import { Foto } from "../componentes";
import { enlaceBusqueda, enlaceProducto } from "../enrutador";
import { aRenglones } from "../lista_texto";
import { CANASTA } from "../medicion";

const CLAVE = "comparador_lista_items";

const EJEMPLO = [
  { texto: "aceite de maravilla miraflores 900 ml", cantidad: 1 },
  { texto: "leche colun entera 1 l", cantidad: 2 },
  { texto: "nescafe tradicion 170 g", cantidad: 1 },
];

let siguienteId = 1;
const conId = (item) => ({ ...item, id: `r${siguienteId++}` });

export default function Lista() {
  const [items, setItems] = useState(() => {
    try {
      const guardado = JSON.parse(localStorage.getItem(CLAVE) || "null");
      if (Array.isArray(guardado) && guardado.length) return guardado.map(conId);
    } catch { /* un guardado corrupto no debe dejar la pantalla en blanco */ }
    return EJEMPLO.map(conId);
  });
  const [modo, setModo] = useState("escribir");
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    localStorage.setItem(CLAVE, JSON.stringify(
      items.filter((i) => i.texto.trim()).map(({ texto, cantidad }) => ({ texto, cantidad }))));
  }, [items]);

  const validos = items.filter((i) => i.texto.trim().length > 1);

  const agregar = (nuevos) => setItems((previos) => {
    const limpios = previos.filter((i) => i.texto.trim().length > 1);
    return [...limpios, ...nuevos.map(conId)].slice(0, 100);
  });

  async function comparar() {
    if (validos.length === 0) return;
    setCargando(true);
    setError(null);
    try {
      setResultado(await compararLista(
        validos.map(({ texto, cantidad }) => ({ texto: texto.trim(), cantidad }))));
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
          Arma tu lista y te decimos cuánto sale en cada cadena y qué conviene comprar
          en cada una. Puedes escribirla, pegarla, subir un archivo o fotografiarla.
        </p>
      </div>

      <section className="bloque">
        <div className="pestanas" role="tablist" aria-label="Cómo agregar productos">
          {[
            ["escribir", "Escribir o pegar"],
            ["archivo", "Subir un archivo"],
            ["foto", "Desde una foto"],
          ].map(([clave, etiqueta]) => (
            <button key={clave} type="button" role="tab" aria-selected={modo === clave}
                    onClick={() => setModo(clave)}>
              {etiqueta}
            </button>
          ))}
        </div>

        {modo === "escribir" && <PegarTexto onAgregar={agregar} />}
        {modo === "archivo" && <SubirArchivo onAgregar={agregar} />}
        {modo === "foto" && <DesdeFoto onAgregar={agregar} />}
      </section>

      <section className="bloque">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
          <h2>Tu lista</h2>
          <span className="secundario">
            {validos.length === 0
              ? "todavía vacía"
              : `${validos.length} ${validos.length === 1 ? "producto" : "productos"}`}
            {" · se guarda solo en este navegador"}
          </span>
        </div>

        <Renglones items={items} setItems={setItems} />

        <div className="fila-chips">
          <button type="button" className="chip"
                  onClick={() => setItems((p) => [...p, conId({ texto: "", cantidad: 1 })])}>
            Agregar un producto
          </button>
          {validos.length > 0 && (
            <button type="button" className="chip"
                    onClick={() => { setItems([]); setResultado(null); }}>
              Vaciar la lista
            </button>
          )}
        </div>

        <button type="button" className="boton" disabled={cargando || validos.length === 0}
                onClick={comparar}>
          {cargando ? "Comparando…" : "Comparar mi lista"}
        </button>
      </section>

      {error && (
        <div role="alert" className="aviso">
          <span aria-hidden="true" className="signo">!</span>
          <div className="cuerpo">
            <strong>No pudimos comparar tu lista</strong>
            <span className="secundario medio">
              Tu lista sigue guardada. Vuelve a intentarlo. ({error})
            </span>
          </div>
        </div>
      )}

      {resultado && <Resultado datos={resultado} />}
    </main>
  );
}

/* ── Entrada ─────────────────────────────────────────────────────────────── */

function Renglones({ items, setItems }) {
  if (items.length === 0) {
    return (
      <p className="medio">
        Tu lista está vacía. Escribe un producto, pega varias líneas o sube el archivo
        o la foto de una lista.
      </p>
    );
  }
  const cambiar = (id, cambio) =>
    setItems((previos) => previos.map((i) => (i.id === id ? { ...i, ...cambio } : i)));

  return (
    <div className="renglones">
      {items.map((item, i) => (
        <div key={item.id} className="renglon">
          <input type="text" value={item.texto} placeholder="Ej.: arroz grado 1 tucapel 1 kg"
                 aria-label={`Producto ${i + 1}`}
                 onChange={(e) => cambiar(item.id, { texto: e.target.value })} />
          <div className="contador">
            <button type="button" aria-label="Quitar una unidad" disabled={item.cantidad <= 1}
                    onClick={() => cambiar(item.id, { cantidad: Math.max(1, item.cantidad - 1) })}>
              −
            </button>
            <span className="valor">{item.cantidad}</span>
            <button type="button" aria-label="Agregar una unidad" disabled={item.cantidad >= 99}
                    onClick={() => cambiar(item.id, { cantidad: Math.min(99, item.cantidad + 1) })}>
              +
            </button>
          </div>
          <button type="button" className="quitar"
                  aria-label={`Quitar ${item.texto || "este producto"}`}
                  onClick={() => setItems((p) => p.filter((x) => x.id !== item.id))}>
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

function PegarTexto({ onAgregar }) {
  const [texto, setTexto] = useState("");
  const renglones = aRenglones(texto);
  return (
    <div className="columna gap-12">
      <label htmlFor="pegado" className="secundario">
        Un producto por línea. Si escribes «2 leche colun» o «leche colun x2», tomamos
        la cantidad.
      </label>
      <textarea id="pegado" value={texto} onChange={(e) => setTexto(e.target.value)}
                placeholder={"arroz grado 1 tucapel 1 kg\n2 leche colun entera 1 l\naceite de maravilla 900 ml"} />
      <button type="button" className="boton" disabled={renglones.length === 0}
              onClick={() => { onAgregar(renglones); setTexto(""); }}>
        {renglones.length === 0
          ? "Agregar a la lista"
          : `Agregar ${renglones.length} ${renglones.length === 1 ? "producto" : "productos"}`}
      </button>
    </div>
  );
}

function SubirArchivo({ onAgregar }) {
  const [encima, setEncima] = useState(false);
  const [aviso, setAviso] = useState(null);
  const entrada = useRef(null);

  async function leer(archivo) {
    if (!archivo) return;
    if (/\.(xlsx|xls|ods)$/i.test(archivo.name)) {
      setAviso("Las planillas de Excel no se leen directamente. Ábrela y guárdala como CSV, que sí leemos.");
      return;
    }
    const texto = await archivo.text();
    const renglones = aRenglones(texto);
    if (renglones.length === 0) {
      setAviso("No encontramos productos en ese archivo. Debe tener un producto por línea.");
      return;
    }
    setAviso(null);
    onAgregar(renglones);
  }

  return (
    <div className="columna gap-12">
      <div className={`zona-archivo${encima ? " encima" : ""}`}
           onDragOver={(e) => { e.preventDefault(); setEncima(true); }}
           onDragLeave={() => setEncima(false)}
           onDrop={(e) => { e.preventDefault(); setEncima(false); leer(e.dataTransfer.files[0]); }}>
        <strong>Arrastra aquí tu archivo</strong>
        <span className="secundario">
          Texto o CSV, con un producto por línea. El archivo se lee en tu navegador y no
          se envía a ninguna parte.
        </span>
        <input ref={entrada} type="file" accept=".txt,.csv,text/plain,text/csv"
               style={{ display: "none" }} onChange={(e) => leer(e.target.files[0])} />
        <button type="button" className="boton secundario" onClick={() => entrada.current.click()}>
          Elegir un archivo
        </button>
      </div>
      {aviso && <p className="secundario medio" role="status">{aviso}</p>}
    </div>
  );
}

/**
 * Lectura de una lista fotografiada.
 *
 * El reconocimiento corre dentro del navegador: la fotografía no se envía a ningún
 * servidor, tampoco al nuestro. Importa porque una lista de compras o una boleta
 * pueden traer datos que no tenemos por qué ver, y porque el sistema declara no tratar
 * datos personales. El costo es que la primera vez hay que descargar el modelo del
 * idioma y que el reconocimiento tarda unos segundos.
 */
function DesdeFoto({ onAgregar }) {
  const [estado, setEstado] = useState("inicio");
  const [avance, setAvance] = useState(0);
  const [lineas, setLineas] = useState([]);
  const [fallo, setFallo] = useState(null);
  const entrada = useRef(null);

  async function reconocer(archivo) {
    if (!archivo) return;
    setEstado("leyendo");
    setAvance(0);
    setFallo(null);
    setLineas([]);
    let worker;
    try {
      const { createWorker } = await import("tesseract.js");
      worker = await createWorker("spa", 1, {
        logger: (m) => {
          if (m.status === "recognizing text") setAvance(Math.round(m.progress * 100));
        },
      });
      const { data } = await worker.recognize(archivo);
      const encontradas = aRenglones(data.text || "");
      if (encontradas.length === 0) {
        setFallo("No pudimos leer productos en esa foto. Prueba con más luz, más cerca y con la lista derecha.");
        setEstado("inicio");
      } else {
        setLineas(encontradas);
        setEstado("revisar");
      }
    } catch (e) {
      setFallo(`No se pudo completar el reconocimiento (${e.message}). Puedes escribir la lista a mano.`);
      setEstado("inicio");
    } finally {
      if (worker) { try { await worker.terminate(); } catch { /* ya terminó */ } }
    }
  }

  if (estado === "leyendo") {
    return (
      <div className="columna gap-12">
        <p role="status">Leyendo la foto… {avance}%</p>
        <span className="progreso"><span style={{ width: `${Math.max(4, avance)}%` }} /></span>
        <span className="secundario">
          La primera vez se descarga el modelo del idioma; después es más rápido.
        </span>
      </div>
    );
  }

  if (estado === "revisar") {
    return (
      <div className="columna gap-12">
        <p className="medio">
          Esto es lo que leímos. El reconocimiento se equivoca con la letra manuscrita,
          así que conviene revisarlo antes de agregarlo.
        </p>
        <ul className="columna gap-4" style={{ margin: 0, paddingLeft: 20 }}>
          {lineas.map((l, i) => (
            <li key={i}>{l.cantidad > 1 ? `${l.cantidad} × ` : ""}{l.texto}</li>
          ))}
        </ul>
        <div className="fila-chips">
          <button type="button" className="boton"
                  onClick={() => { onAgregar(lineas); setEstado("inicio"); setLineas([]); }}>
            Agregar {lineas.length} a la lista
          </button>
          <button type="button" className="chip"
                  onClick={() => { setEstado("inicio"); setLineas([]); }}>
            Descartar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="columna gap-12">
      <div className="zona-archivo">
        <strong>Fotografía tu lista</strong>
        <span className="secundario">
          Sirve una lista escrita a mano o una boleta. La foto se procesa en tu propio
          navegador y no se sube a ningún servidor.
        </span>
        <input ref={entrada} type="file" accept="image/*" capture="environment"
               style={{ display: "none" }} onChange={(e) => reconocer(e.target.files[0])} />
        <button type="button" className="boton secundario" onClick={() => entrada.current.click()}>
          Elegir una foto
        </button>
      </div>
      {fallo && <p className="secundario medio" role="status">{fallo}</p>}
    </div>
  );
}

/* ── Resultado ───────────────────────────────────────────────────────────── */

function Resultado({ datos }) {
  const entran = datos.items.filter((i) => i.entra_al_total);
  const fuera = datos.items.filter((i) => i.producto && !i.entra_al_total);
  const sinReconocer = datos.items.filter((i) => !i.producto);
  const masCara = datos.totales[datos.totales.length - 1];
  const masBarata = datos.totales[0];

  return (
    <>
      <section className="columna gap-12">
        <h2>Cómo quedó tu lista</h2>
        <div className="recuento">
          <Recuento n={entran.length}
                    titulo={entran.length === 1 ? "entra al total" : "entran al total"}
                    detalle="Tienen precio en todas las cadenas." />
          <Recuento n={fuera.length}
                    titulo={fuera.length === 1 ? "queda fuera" : "quedan fuera"}
                    detalle={fuera.length
                      ? "Los reconocimos, pero falta el precio en alguna cadena."
                      : "Todo lo reconocido está en las tres."} />
          <Recuento n={sinReconocer.length} titulo="sin reconocer"
                    detalle={sinReconocer.length
                      ? "No encontramos un producto que corresponda."
                      : "Todo lo que escribiste lo encontramos."} />
        </div>

        {fuera.length > 0 && entran.length > 0 && (
          <div className="bloque">
            <strong>
              Por qué el total suma {entran.length} de tus {datos.items.length} productos
            </strong>
            <p className="medio">
              Para comparar, las tres canastas tienen que tener lo mismo.{" "}
              {fuera[0].producto?.nombre} no tiene precio en{" "}
              {fuera[0].cadenas_que_faltan.join(" ni ") || "alguna cadena"}: si lo
              sumáramos en las demás, esa cadena parecería más barata solo porque su
              canasta tiene un producto menos.
            </p>
          </div>
        )}
      </section>

      {datos.totales.length > 0 && (
        <>
          <section className="columna gap-12">
            <h2>Si compras todo en un solo lugar</h2>
            <div className="bloque">
              <div className="columna gap-4">
                <span className="marbarato">Lo más conveniente es {datos.cadena_recomendada}</span>
                <span className="precio-ganador detalle">{pesos(masBarata.total)}</span>
              </div>
              <div className="columna gap-8">
                {datos.totales.map((t) => (
                  <div key={t.cadena}
                       className={`fila-cadena${t.cadena === datos.cadena_recomendada ? " mejor" : ""}`}>
                    <span className="nombre">
                      {t.cadena}
                      {t.cadena === datos.cadena_recomendada &&
                        <span className="solo-lectores"> (la más barata)</span>}
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
            <h2>Si repartes la compra</h2>
            <div className="bloque">
              <div className="columna gap-4">
                <span className="marbarato">Cada producto donde está más barato</span>
                <span className="precio-ganador detalle">{pesos(datos.total_optimo)}</span>
              </div>
              <div className="renglones">
                {entran.map((item, i) => {
                  const p = item.producto;
                  const mejor = p.precios.find((x) => x.precio === p.menor_precio);
                  return (
                    <div key={`${i}-${item.texto}`}
                         style={{ display: "flex", gap: 12, alignItems: "center" }}>
                      <Foto producto={p} clase="chica" />
                      <div className="columna" style={{ flex: 1, minWidth: 0, gap: 2 }}>
                        <a href={enlaceProducto(p.id)}>{p.nombre}</a>
                        <span className="secundario">
                          en {mejor?.cadena}
                          {item.cantidad > 1 ? ` · ${item.cantidad} unidades` : ""}
                        </span>
                      </div>
                      <span className="num" style={{ fontWeight: 700, color: "var(--save)" }}>
                        {pesos(p.menor_precio * item.cantidad)}
                      </span>
                    </div>
                  );
                })}
              </div>
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
              Lo medimos en una canasta de {CANASTA.productos} productos con precio en
              las tres cadenas, contra comprar todo en la más cara.
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
            No encontramos un producto que corresponda con certeza. Preferimos no
            adivinar: un emparejamiento equivocado te daría un precio que no es. Busca
            estas líneas a mano y agrégalas con el nombre que usa la tienda.
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

function Recuento({ n, titulo, detalle }) {
  return (
    <div>
      <strong className="cifra">{numero(n)}</strong>
      <span className="secundario" style={{ fontWeight: 600, color: "var(--text-medio)" }}>{titulo}</span>
      <span className="secundario">{detalle}</span>
    </div>
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
            <span className="secundario">
              Escribiste «{item.texto}»{item.cantidad > 1 ? ` · ${item.cantidad} unidades` : ""}
            </span>
            <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <Foto producto={p} clase="chica" />
              <div className="encabezado-meta">
                <a href={enlaceProducto(p.id)} style={{ fontWeight: 600 }}>{p.nombre}</a>
                {p.formato && <span className="pill formato">{p.formato}</span>}
              </div>
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
                    {cadena} {pesos(dato.precio)}
                    {esMenor && <span className="solo-lectores"> (el más barato)</span>}
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
