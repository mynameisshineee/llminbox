// Casos del pelador de titulares, cada uno con la convención real que lo produjo
// y —donde lo hubo— el fallo que lo puso aquí. Se corre con:
//   node web/src/lib/titular.test.mjs
// No necesita marco de tests: importa el fichero real quitándole las anotaciones
// de tipo, para que no exista una segunda copia de la lógica que pueda derivar.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const aqui = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(aqui, "titular.ts"), "utf8");
const cuerpo = src
  .slice(src.indexOf("const TIPOS_ETIQUETA"), src.indexOf("/** Hora relativa"))
  .replace("export function titular(cabecera: string, actor: string | null): string", "function titular(cabecera, actor)")
  .replace("const gasta = (k: keyof typeof cupo, rx: RegExp) =>", "const gasta = (k, rx) =>");
const { titular } = await import("data:text/javascript," + encodeURIComponent(cuerpo + "\nexport {titular};"));

const CASOS = [
  // [cabecera, actor, esperado, por qué está aquí]
  ["### [alice → bob · PRODUCED] 2026-07-27T10:15:00Z — pagos: endpoint listo", "alice",
   "pagos: endpoint listo", "la convención dominante, 94% del corpus"],

  ["## [wiki-vault 2026-07-28T01:34:01Z] 🌙 EN VUELO — mandato del operador", "wiki-vault",
   "EN VUELO — mandato del operador", "el corchete cierra DESPUÉS del sello: dejaba «] 🌙…»"],

  ["### [MSG cfo-guardian->TODOS] 2026-06-18 — alcance ampliado", "cfo-guardian",
   "alcance ampliado", "el separador se comía el «-» de «->» y dejaba «>TODOS]…»"],

  ["### [CLAIM deploy-bik.eus] [bikeus] 2026-07-09T22:15:29Z — deploy fix copy", "deploy-bik.eus",
   "deploy fix copy", "DOS grupos entre corchetes seguidos: dejaba «[bikeus]…»"],

  ["## 2026-05-25 — [STATUS BE→FE] ADR-022 firma flip COMPLETE", "be",
   "ADR-022 firma flip COMPLETE", "el sello va DELANTE del corchete: orden invertido"],

  ["### [marketing -> cpo (RESP HOLD signup: carril limpio)] 2026-07-13T16:39:30Z — status: RESP (compliant)", "marketing",
   "status: RESP (compliant)", "STATUS y RESP son palabras reales aquí, no etiquetas"],

  ["### [cpo → marketing ∧ bikeus (nota larga entre paréntesis que ocupa bastante más de ciento sesenta caracteres para comprobar que el tope no se queda corto y la ruta se pela entera igual)] 2026-07-10T14:09:55Z — el titular de verdad", "cpo",
   "el titular de verdad", "rutas de mediana 269 caracteres: el tope de 160 las partía"],

  ["## 2026-07-28T10:30:00Z \u00b7 transcribo \u2192 wiki-vault \u00b7 PRODUCED \u2014 rescate de 11 v\u00eddeos", "transcribo",
   "rescate de 11 v\u00eddeos", "ruta del spoke SIN corchete: abr\u00eda por «wiki-vault \u00b7 PRODUCED \u2014»"],

  ["## 2026-07-06T11:45Z · transcribo → wiki-vault · PRODUCED", "transcribo",
   "", "cabecera de PURO metadato: vacío, y quien llama usa el cuerpo"],

  ["### [qa] ACK recibido, arranco", "qa",
   "ACK recibido, arranco", "ACK abre texto libre y NO debe pelarse como etiqueta"],
];

let fallos = 0;
for (const [head, actor, esperado, porque] of CASOS) {
  const dado = titular(head, actor);
  if (dado === esperado) {
    console.log(`  ✓ ${porque}`);
  } else {
    fallos++;
    console.log(`  ✗ ${porque}`);
    console.log(`      cabecera: ${JSON.stringify(head.slice(0, 96))}`);
    console.log(`      esperado: ${JSON.stringify(esperado)}`);
    console.log(`      obtenido: ${JSON.stringify(dado)}`);
  }
}

// CONTROL POSITIVO: si el pelador devolviera siempre la cabecera en crudo —el fallo
// más plausible al tocarlo— los casos de arriba fallarían. Se comprueba que al menos
// uno depende de verdad de pelar algo, para que este fichero no pueda dar verde
// midiendo la nada.
const crudo = titular("### [alice → bob · PRODUCED] 2026-07-27T10:15:00Z — pagos: endpoint listo", "alice");
if (crudo.includes("alice") || crudo.includes("2026-")) {
  console.log("  ✗ control positivo: el pelador no está pelando nada");
  fallos++;
} else {
  console.log("  ✓ control positivo: el resultado no conserva actor ni sello");
}

console.log(fallos === 0 ? `\ntitulares: ${CASOS.length + 1} casos, todo verde` : `\ntitulares: ${fallos} fallo(s)`);
process.exit(fallos === 0 ? 0 : 1);
