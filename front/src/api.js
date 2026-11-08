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

export const obtenerEstado = () => pedir("/salud");

export const buscarProductos = (consulta) =>
  pedir(`/buscar?q=${encodeURIComponent(consulta)}&limite=20`);

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

export const pesos = (valor) =>
  valor == null ? "" : `$${valor.toLocaleString("es-CL")}`;
