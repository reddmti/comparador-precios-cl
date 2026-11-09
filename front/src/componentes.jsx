import { useCallback, useEffect, useState } from "react";

import { fechaLarga, leerProducto, pesos } from "./api";
import { enlaceProducto } from "./enrutador";

/**
 * Pide datos y expone los tres estados que toda pantalla tiene que saber mostrar:
 * cargando, error con reintento, y datos. Centralizarlo evita que cada pantalla
 * invente su propia variante y que alguna olvide el reintento.
 */
export function usePeticion(hacer, dependencias) {
  const [estado, setEstado] = useState({ cargando: true, error: null, datos: null });
  const [intento, setIntento] = useState(0);

  const ejecutar = useCallback(hacer, dependencias);

  useEffect(() => {
    let vigente = true;
    setEstado((previo) => ({ ...previo, cargando: true, error: null }));
    ejecutar()
      .then((datos) => vigente && setEstado({ cargando: false, error: null, datos }))
      .catch((e) => vigente && setEstado({ cargando: false, error: e.message, datos: null }));
    return () => { vigente = false; };
  }, [ejecutar, intento]);

  return { ...estado, reintentar: () => setIntento((n) => n + 1) };
}

/**
 * Foto del producto, servida por la cadena de origen.
 *
 * Se guarda solo la dirección, nunca el archivo, así que la imagen puede no llegar:
 * la cadena puede moverla, bloquear el enlace desde otro sitio o simplemente no tener
 * foto para ese producto. El marco reserva el espacio desde el principio para que la
 * tarjeta no salte al cargar, y si falla queda la inicial en lugar de un hueco roto.
 */
export function Foto({ producto, clase = "" }) {
  const [falla, setFalla] = useState(false);
  const url = producto.imagen_url;
  return (
    <div className={`foto ${clase}`.trim()}>
      {url && !falla ? (
        <img src={url} alt="" loading="lazy" decoding="async"
             referrerPolicy="no-referrer" onError={() => setFalla(true)} />
      ) : (
        <span className="inicial" aria-hidden="true">{(producto.nombre || "?").trim()[0]}</span>
      )}
    </div>
  );
}

export function Cargando({ texto, tarjetas = 4 }) {
  return (
    <>
      <p role="status" className="secundario">{texto}</p>
      <div className="grilla-productos" aria-hidden="true">
        {Array.from({ length: tarjetas }, (_, i) => (
          <div key={i} className="tarjeta">
            <div className="cabeza">
              <div className="hueso" style={{ width: 84, height: 84, flex: "none" }} />
              <div className="columna gap-8" style={{ flex: 1 }}>
                <div className="hueso" style={{ height: 16, width: "90%" }} />
                <div className="hueso" style={{ height: 14, width: "45%" }} />
              </div>
            </div>
            <div className="hueso" style={{ height: 32, width: "55%" }} />
            <div className="columna gap-8">
              <div className="hueso" style={{ height: 10 }} />
              <div className="hueso" style={{ height: 10 }} />
              <div className="hueso" style={{ height: 10 }} />
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

export function ErrorCarga({ mensaje, termino, reintentar }) {
  return (
    <div role="alert" className="aviso">
      <span aria-hidden="true" className="signo">!</span>
      <div className="cuerpo">
        <strong>No pudimos cargar los precios</strong>
        <span className="secundario medio">
          {termino
            ? `Puede ser tu conexión o un problema de nuestro lado. Tu búsqueda «${termino}» sigue aquí; vuelve a intentarlo en unos segundos.`
            : "Puede ser tu conexión o un problema de nuestro lado. Vuelve a intentarlo en unos segundos."}
          {mensaje ? ` (${mensaje})` : ""}
        </span>
        <div className="fila-chips" style={{ marginTop: 6 }}>
          <button type="button" className="boton" onClick={reintentar}>Reintentar</button>
          <a className="boton secundario" href="#/categorias">Ver categorías</a>
        </div>
      </div>
    </div>
  );
}

export function Migas({ pasos }) {
  return (
    <nav className="migas" aria-label="Ruta">
      {pasos.map((paso, i) => (
        <span key={paso.texto} style={{ display: "flex", gap: 6 }}>
          {paso.href ? <a href={paso.href}>{paso.texto}</a> : <span aria-current="page">{paso.texto}</span>}
          {i < pasos.length - 1 && <span aria-hidden="true">/</span>}
        </span>
      ))}
    </nav>
  );
}

/** Una fila «cadena · barra · precio». La barra mide el precio contra el mayor. */
export function FilaCadena({ fila }) {
  if (!fila.dato) {
    return (
      <div role="listitem" className="fila-cadena sin-dato">
        <span className="nombre" style={{ color: "var(--muted)" }}>{fila.cadena}</span>
        <span className="sin-info">sin información</span>
      </div>
    );
  }
  return (
    <div role="listitem" className={`fila-cadena${fila.esMenor ? " mejor" : ""}`}>
      <span className="nombre">{fila.esMenor ? `✓ ${fila.cadena}` : fila.cadena}</span>
      <span className="barra" aria-hidden="true"><span style={{ width: fila.ancho }} /></span>
      <span className="valor">{pesos(fila.dato.precio)}</span>
    </div>
  );
}

export function TarjetaProducto({ producto }) {
  const p = leerProducto(producto);
  return (
    <article className="tarjeta">
      <div className="cabeza">
        <Foto producto={p} />
        <header>
          <h3>{p.nombre}</h3>
          <div className="encabezado-meta">
            {p.formato && <span className="pill formato">{p.formato}</span>}
            <span className="secundario">{p.cobertura}</span>
          </div>
        </header>
      </div>

      {p.comparable && (
        <div className="resumen">
          <div className="columna" style={{ gap: 2 }}>
            <span className="marbarato">✓ Más barato en {p.cadena_mas_barata}</span>
            <span className="precio-ganador">{pesos(p.menor_precio)}</span>
          </div>
          <span className={`pill ${p.minima ? "minima" : "ahorro"}`}>{p.diferencia}</span>
        </div>
      )}

      {p.solo && (
        <div className="columna" style={{ gap: 2 }}>
          <span className="secundario medio" style={{ fontWeight: 600 }}>
            Solo en {p.cadena_mas_barata} · no se puede comparar
          </span>
          <span className="precio-ganador solo">{pesos(p.menor_precio)}</span>
        </div>
      )}

      <div role="list" className="filas-cadena">
        {p.filas.map((fila) => <FilaCadena key={fila.cadena} fila={fila} />)}
      </div>

      <a className="enlace-bloque" href={enlaceProducto(p.id)}>
        Ver precio por unidad, tiendas e historial →
      </a>
    </article>
  );
}

/**
 * Fecha de los datos, o el aviso de atraso cuando pasó más de un día.
 *
 * El aviso reemplaza a la fecha en vez de acompañarla, y se distingue por un borde
 * grueso y no por un color nuevo: el rojo y el amarillo ya significan otra cosa en una
 * pantalla donde el verde marca el precio más bajo.
 */
export function EstadoDeLosDatos({ estado, dias }) {
  if (!estado?.ultima_actualizacion) return null;
  if (dias != null && dias > 1) {
    return (
      <div role="status" className="aviso">
        <span aria-hidden="true" className="signo">!</span>
        <div className="cuerpo">
          <strong>Los precios son del {fechaLarga(estado.ultima_actualizacion)}, hace {dias} días.</strong>
          <span className="secundario medio">
            La actualización diaria está atrasada. Los precios en tienda pueden haber
            cambiado; revisa el enlace de cada cadena antes de decidir.
          </span>
        </div>
      </div>
    );
  }
  return (
    <div className="columna" style={{ gap: 2 }}>
      <span className="cifra">{fechaLarga(estado.ultima_actualizacion)}</span>
      <span className="secundario">precios de hoy · se actualizan una vez al día</span>
    </div>
  );
}
