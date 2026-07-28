import type { Estado } from "@/lib/api";

/** La cabecera repite en prosa lo que ya sale como metadatos («[🔎📊qa · DIAGNÓSTICO…»
 *  cuando la fila de meta ya dice «qa →»). Enseñar dos veces lo mismo es lo que hace
 *  ilegible una lista de miles de ensayos, así que se pela por capas: corchete,
 *  emoji, la ETIQUETA de tipo si abre la cabecera, el propio actor, la flecha con
 *  sus destinos, el corchete de cierre suelto, y el sello. Portado tal cual de
 *  `ui.html` (`titular`) — verificado contra 1.619 entradas reales de los 6
 *  ledgers: 811 cabeceras rotas → 207, cero casos donde el resultado empeorase.
 *  No reintentar tras pelar el actor: una versión que lo hacía se comía
 *  "ACK"/"DONE"/"HANDOFF" cuando eran texto libre genuino, no la etiqueta. */
const ETIQUETAS =
  /^(HEARTBEAT|CARRY-FORWARD|CLAIM|CANON|CERT|DONE|RESP|AVISO|MSG|ASK|ACK|STATUS|INFO|HANDOFF)(?:[/·-]\s*(?:HEARTBEAT|CARRY-FORWARD|CLAIM|CANON|CERT|DONE|RESP|AVISO|MSG|ASK|ACK|STATUS|INFO|HANDOFF))*\b\s*/i;

export function titular(cabecera: string, actor: string | null): string {
  let t = (cabecera ?? "").replace(/^#{2,3}\s*/, "").replace(/^\[\s*/, "");
  t = t.replace(/^[\p{Extended_Pictographic}\p{Emoji_Presentation}️‍\s]+/u, "");
  t = t.replace(ETIQUETAS, "");
  if (actor) {
    const esc = actor.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    t = t.replace(new RegExp(`^${esc}\\b\\s*[·:—–-]?\\s*`, "i"), "");
  }
  t = t.replace(/^(?:→|->)[^\]]{0,160}?\]\s*/, "");
  t = t.replace(/^\]\s*/, "");
  t = t.replace(/^\d{4}-\d{2}-\d{2}T?[\d:]*Z?\s*[—–-]?\s*/, "");
  t = t.replace(/^[\p{Extended_Pictographic}️\s·—–-]+/u, "");
  return t.trim() || (cabecera ?? "").replace(/^#{2,3}\s*/, "").slice(0, 160);
}

/** Hora relativa: hoy → HH:MM, esta semana → "Nd", si no, fecha corta. Portado de
 *  `ui.html` (`hora`) — mejora sobre el slice(11,16) del skeleton, que vuelve
 *  ilegible cualquier entrada de más de un día (un ledger de 37.000 entradas no
 *  es todo de hoy). */
export function hora(ts: string | null): string {
  if (!ts) return "·";
  const d = new Date(`${ts}Z`);
  const dias = Math.floor((Date.now() - d.getTime()) / 864e5);
  if (dias === 0) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (dias < 7) return `${dias}d`;
  return d.toLocaleDateString([], { day: "2-digit", month: "short" });
}

export type MotivoVacio = "sin-ledgers" | "sin-entradas" | "filtro-vacio";

/** Cuál de los tres estados vacíos aplica. Mira el ledger SELECCIONADO, no el total
 *  global: un ledger de 0 entradas entre otros con datos no es "filtro vacío" — bug
 *  específico ya cazado y corregido en `ui.html` (comentario "medido en vivo").
 *  Portar la función completa, no reinventarla [brief §5.8]. */
export function motivoVacio(args: {
  ledgersConfigurados: number;
  filtrosActivos: boolean;
  estado: Estado[];
  ledgerSeleccionado: string;
}): MotivoVacio {
  if (args.ledgersConfigurados === 0) return "sin-ledgers";
  const relevantes = args.ledgerSeleccionado
    ? args.estado.filter((x) => x.ledger === args.ledgerSeleccionado)
    : args.estado;
  const totalRelevante = relevantes.reduce((a, x) => a + x.entradas, 0);
  if (!args.filtrosActivos && totalRelevante === 0) return "sin-entradas";
  return "filtro-vacio";
}
