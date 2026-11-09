/*
 * Interpretación del texto de una lista de compras.
 *
 * Va aparte de la pantalla porque es lógica con casos que vale la pena probar sueltos:
 * lo que escribe una persona, lo que trae un archivo y lo que devuelve el
 * reconocimiento de una foto pasan todos por aquí.
 */

// Un número seguido de una de estas palabras es el formato del producto y no la
// cantidad que se quiere comprar. Sin esta distinción, «500 g de azúcar» se leería
// como quinientas bolsas.
const UNIDADES = "kg|kilos?|g|gr|grs|gramos?|ml|cc|l|lt|lts|litros?|un|u|uds?|unidades?|m|mt|mts";

const CANTIDAD_ADELANTE = new RegExp(`^(\\d{1,2})\\s*(?:x|×)?\\s+(?!(?:${UNIDADES})\\b)(.+)$`, "i");
const CANTIDAD_ATRAS = /^(.+?)\s*(?:x|×)\s*(\d{1,2})$/i;
const CANTIDAD_PARENTESIS = /^(.+?)\s*\((\d{1,2})\)$/;

/**
 * Arregla las confusiones que deja el reconocimiento de una foto.
 *
 * La ele minúscula suelta se lee casi siempre como barra vertical o como uno, de modo
 * que «leche 1 l» vuelve como «leche 1 |». Solo se corrige cuando el carácter va solo
 * y después de un número, que es donde se escribe la unidad: así no se toca un nombre
 * de producto que legítimamente traiga uno de esos signos.
 */
function limpiarReconocimiento(linea) {
  return linea
    .replace(/(\d\s*)[|¦]\b/g, "$1l")
    .replace(/(\d\s*)[|¦]$/g, "$1l");
}

/**
 * Separa la cantidad del nombre en una línea escrita a mano.
 *
 * La gente anota la cantidad de tres maneras —«2 leche», «leche x2», «leche (2)»— y
 * ninguna es la que espera la API. Se reconocen las tres, cuidando de no confundirla
 * con el formato: «1 kg de azúcar» es un producto, no uno de un kilo.
 */
export function interpretar(linea) {
  const limpio = limpiarReconocimiento(linea).replace(/^[\s*·•\-–—]+/, "").trim();
  for (const [patron, iTexto, iCantidad] of [
    [CANTIDAD_ADELANTE, 2, 1],
    [CANTIDAD_ATRAS, 1, 2],
    [CANTIDAD_PARENTESIS, 1, 2],
  ]) {
    const m = limpio.match(patron);
    if (m) {
      const cantidad = Math.min(99, Math.max(1, parseInt(m[iCantidad], 10)));
      const texto = m[iTexto].replace(/^de\s+/i, "").trim();
      if (texto.length > 1) return { texto, cantidad };
    }
  }
  return { texto: limpio, cantidad: 1 };
}

/**
 * Convierte un texto pegado, un .txt, un .csv o el resultado del reconocimiento de una
 * foto en renglones de lista.
 *
 * Se descartan las líneas que son solo números o signos, que en una boleta son los
 * precios y los totales, y en una lista escrita a mano los encabezados numerados.
 */
export function aRenglones(texto) {
  return texto
    .split(/\r?\n/)
    .map((l) => l.split(/[;,\t]/)[0])
    .map((l) => l.trim())
    .filter((l) => l.length > 1 && !/^[\d\s$.,:-]+$/.test(l))
    .map(interpretar)
    .filter((r) => r.texto.length > 1);
}
