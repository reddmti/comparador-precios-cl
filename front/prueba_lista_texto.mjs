/*
 * Pruebas del analizador de listas y del reconocimiento de una foto.
 *
 *   node prueba_lista_texto.mjs            solo el analizador, instantáneo
 *   node prueba_lista_texto.mjs --ocr ruta añade el reconocimiento de esa imagen
 *
 * El reconocimiento se deja aparte porque descarga el modelo del idioma y tarda
 * varios segundos, mientras que el analizador es el que se rompe al editarlo.
 */
import { interpretar, aRenglones } from "./src/lista_texto.js";

let fallas = 0;

function igual(obtenido, esperado, caso) {
  const a = JSON.stringify(obtenido);
  const b = JSON.stringify(esperado);
  if (a === b) {
    console.log(`  ok    ${caso}`);
  } else {
    fallas++;
    console.log(`  FALLA ${caso}\n          esperado ${b}\n          obtenido ${a}`);
  }
}

console.log("Cantidad escrita de las tres maneras");
igual(interpretar("2 leche colun entera 1 l"), { texto: "leche colun entera 1 l", cantidad: 2 }, "delante");
igual(interpretar("leche colun x2"), { texto: "leche colun", cantidad: 2 }, "detrás con x");
igual(interpretar("leche colun (3)"), { texto: "leche colun", cantidad: 3 }, "entre paréntesis");
igual(interpretar("2 x leche colun"), { texto: "leche colun", cantidad: 2 }, "delante con x");
igual(interpretar("12 huevos"), { texto: "huevos", cantidad: 12 }, "dos dígitos");

console.log("\nEl formato no es una cantidad");
igual(interpretar("1 kg de arroz"), { texto: "1 kg de arroz", cantidad: 1 }, "kg");
igual(interpretar("500 g de azucar"), { texto: "500 g de azucar", cantidad: 1 }, "g, tres dígitos");
igual(interpretar("2 l de bebida"), { texto: "2 l de bebida", cantidad: 1 }, "litros");
igual(interpretar("6 un de yogurt"), { texto: "6 un de yogurt", cantidad: 1 }, "unidades");

console.log("\nLimpieza de viñetas y renglones");
igual(interpretar("- aceite de maravilla"), { texto: "aceite de maravilla", cantidad: 1 }, "guion");
igual(interpretar("• 2 leche"), { texto: "leche", cantidad: 2 }, "viñeta y cantidad");
igual(aRenglones("arroz\n\n  \n2 leche\n$1.990\n12:30\nx"),
      [{ texto: "arroz", cantidad: 1 }, { texto: "leche", cantidad: 2 }],
      "descarta vacías, precios, horas y líneas de un carácter");
igual(aRenglones("arroz;1\nleche,2"),
      [{ texto: "arroz", cantidad: 1 }, { texto: "leche", cantidad: 1 }],
      "toma la primera columna de un CSV");

const i = process.argv.indexOf("--ocr");
if (i !== -1 && process.argv[i + 1]) {
  const { createWorker } = await import("tesseract.js");
  const { readFileSync } = await import("node:fs");
  console.log("\nReconocimiento de la imagen");
  const worker = await createWorker("spa", 1, {});
  const { data } = await worker.recognize(readFileSync(process.argv[i + 1]));
  await worker.terminate();
  for (const r of aRenglones(data.text)) {
    console.log(`  cantidad ${String(r.cantidad).padStart(2)}  |  ${r.texto}`);
  }
}

console.log(fallas === 0 ? "\nTodo en orden." : `\n${fallas} fallas.`);
process.exit(fallas === 0 ? 0 : 1);
