import { useEffect, useState } from "react";

/**
 * Enrutado por fragmento (#/ruta?parametros).
 *
 * Se usa el fragmento y no el historial del navegador porque el front se publica como
 * sitio estático: con rutas reales, recargar en «/categoria/leche» pediría al servidor
 * un archivo que no existe. El fragmento nunca sale del navegador, de modo que
 * cualquier URL del sitio se puede recargar y compartir sin configurar reescrituras.
 */
export function useRuta() {
  const [hash, setHash] = useState(() => window.location.hash);

  useEffect(() => {
    const alCambiar = () => setHash(window.location.hash);
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);

  return analizar(hash);
}

export function analizar(hash) {
  const crudo = (hash || "").replace(/^#\/?/, "");
  const [camino, consulta] = crudo.split("?");
  const partes = camino.split("/").filter(Boolean).map(decodeURIComponent);
  const parametros = Object.fromEntries(new URLSearchParams(consulta || ""));
  return { vista: partes[0] || "portada", parametros, partes };
}

export function ir(ruta) {
  window.location.hash = ruta;
}

export const enlaceBusqueda = (termino) => `#/buscar?q=${encodeURIComponent(termino)}`;
export const enlaceCategoria = (nombre) => `#/categoria/${encodeURIComponent(nombre)}`;
export const enlaceProducto = (id) => `#/producto/${id}`;

/** Cada cambio de vista vuelve al principio; si no, se entra a media página. */
export function useSubirAlInicio(dependencia) {
  useEffect(() => { window.scrollTo(0, 0); }, [dependencia]);
}
