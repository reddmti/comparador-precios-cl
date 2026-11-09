/*
 * Cifras del experimento de canasta de E3.
 *
 * Están aquí y no escritas dentro de una pantalla porque son una medición, no una
 * frase de marketing: salen de `_evaluacion/e3_canasta.py` y cualquier cambio en el
 * método obliga a rehacerlas. Si se vuelven a medir, se cambian en este archivo y en
 * el informe, nunca en uno solo.
 *
 * Medición del 08-11-2026, umbral 80 y las cuatro reglas de rechazo.
 */
export const CANASTA = {
  productos: 155,
  // Ambos ahorros se expresan sobre la misma base: comprar todo en la cadena más cara.
  elegirLaMasBarata: 1.6,
  productoAProducto: 11.2,
};
