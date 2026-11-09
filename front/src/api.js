// Acceso a la API. La URL se define en .env (VITE_API_URL) para que el mismo código
// sirva en local y desplegado.

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function pedir(ruta, opciones) {
  const respuesta = await fetch(`${BASE}${ruta}`, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => ({}));
    throw new Error(detalle.detail || `Error ${respuesta.status}`);
  }
  return respuesta.json();
}

function consulta(parametros) {
  const partes = Object.entries(parametros)
    .filter(([, valor]) => valor !== undefined && valor !== null && valor !== "")
    .map(([clave, valor]) => `${clave}=${encodeURIComponent(valor)}`);
  return partes.length ? `?${partes.join("&")}` : "";
}

export const obtenerEstado = () => pedir("/salud");

export const obtenerCategorias = () => pedir("/categorias");

export const obtenerDestacados = (limite = 6, categoria) =>
  pedir(`/destacados${consulta({ limite, categoria })}`);

// Listado de la pantalla de categoría y de la de resultados: el total viene aparte
// de los ítems, porque la página es un recorte del listado completo.
export const listarProductos = ({ q, categoria, cadena, orden = "diferencia", soloComparables = false, limite = 24, desde = 0 }) =>
  pedir(`/productos${consulta({
    q, categoria, cadena, orden, solo_comparables: soloComparables ? "true" : undefined,
    limite, desde,
  })}`);

export const buscarSugerencias = (q) => pedir(`/sugerencias${consulta({ q, limite: 8 })}`);

export const obtenerProducto = (id) => pedir(`/productos/${id}`);

export const obtenerHistorial = (id, dias = 30) =>
  pedir(`/productos/${id}/historial${consulta({ dias })}`);

export const compararLista = (items) =>
  pedir("/listas", {
    method: "POST",
    body: JSON.stringify({ sesion_id: identificadorDeSesion(), items }),
  });

// Identificador anónimo por navegador: el sistema no tiene cuentas ni datos personales.
function identificadorDeSesion() {
  const clave = "comparador_sesion";
  let id = localStorage.getItem(clave);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(clave, id);
  }
  return id;
}

// ── Formato ────────────────────────────────────────────────────────────────
export const pesos = (valor) =>
  valor == null ? "" : `$${valor.toLocaleString("es-CL")}`;

export const numero = (valor) =>
  valor == null ? "" : valor.toLocaleString("es-CL");

export const fechaLarga = (iso) =>
  !iso ? "" : new Date(`${iso}T00:00:00`).toLocaleDateString("es-CL", {
    day: "numeric", month: "long",
  });

export const fechaCorta = (iso) =>
  !iso ? "" : new Date(`${iso}T00:00:00`).toLocaleDateString("es-CL", {
    day: "2-digit", month: "2-digit",
  });

export const diasDesde = (iso) => {
  if (!iso) return null;
  const dia = 24 * 60 * 60 * 1000;
  const hoy = new Date(new Date().toDateString()).getTime();
  return Math.round((hoy - new Date(`${iso}T00:00:00`).getTime()) / dia);
};

// ── Búsquedas recientes, solo en este navegador ────────────────────────────
const CLAVE_RECIENTES = "comparador_recientes";

export function recientes() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_RECIENTES) || "[]");
  } catch {
    return [];
  }
}

export function recordarBusqueda(termino) {
  const limpio = termino.trim();
  if (limpio.length < 2) return;
  const previas = recientes().filter((t) => t.toLowerCase() !== limpio.toLowerCase());
  localStorage.setItem(CLAVE_RECIENTES, JSON.stringify([limpio, ...previas].slice(0, 4)));
}

// ── Lectura de un producto comparado ───────────────────────────────────────
export const CADENAS = ["Jumbo", "Santa Isabel", "Unimarc"];

/**
 * Traduce un producto de la API a lo que las pantallas necesitan mostrar.
 *
 * Deja en un solo lugar las tres reglas de comparación del diseño: la barra se mide
 * contra el precio más alto del propio producto, una diferencia bajo el 5% se declara
 * mínima en vez de celebrarla, y un producto de una sola cadena no se pinta de verde
 * porque no hay nada que comparar.
 */
export function leerProducto(producto) {
  const precios = producto.precios || [];
  const porCadena = Object.fromEntries(precios.map((p) => [p.cadena, p]));
  const menor = producto.menor_precio;
  const mayor = producto.mayor_precio;
  const comparable = precios.length > 1;
  const porcentaje = comparable && menor > 0 ? ((mayor - menor) / mayor) * 100 : 0;
  const minima = comparable && porcentaje < 5;

  return {
    ...producto,
    porCadena,
    comparable,
    solo: precios.length === 1,
    sinPrecio: precios.length === 0,
    porcentaje,
    minima,
    cobertura: textoCobertura(precios.length),
    diferencia: !comparable
      ? null
      : minima
        ? "Diferencia mínima"
        : `Hasta ${pesos(mayor - menor)} menos · ${Math.round(porcentaje)}%`,
    filas: CADENAS.map((cadena) => {
      const dato = porCadena[cadena];
      return {
        cadena,
        dato,
        esMenor: Boolean(dato) && dato.precio === menor && comparable,
        ancho: dato && mayor > 0 ? `${Math.max(6, (dato.precio / mayor) * 100)}%` : "0%",
      };
    }),
  };
}

function textoCobertura(cuantas) {
  if (cuantas === 0) return "sin precio vigente";
  if (cuantas === 1) return "en 1 cadena";
  return `en ${cuantas} cadenas`;
}
