/** Cliente del API de llminbox.
 *
 *  El token lo teclea la persona y vive en el localStorage de su navegador; cada
 *  petición lo manda en la cabecera. Nunca se incrusta en el HTML servido: el
 *  puerto lo alcanza cualquier contenedor de la máquina (medido en Docker Desktop
 *  para macOS), así que regalar el token en la página sería regalarlo a todos.
 */
const CLAVE = "llminbox.token";
export const getToken = () => localStorage.getItem(CLAVE) ?? "";
export const setToken = (t: string) => localStorage.setItem(CLAVE, t);
export const clearToken = () => localStorage.removeItem(CLAVE);

export type Entrada = {
  ledger: string; eid: string; arrival: number; seq: number;
  ts: string | null; actor: string | null; tipo: string | null;
  line_no: number; head: string; body?: string; to?: string[];
};
export type Estado = {
  ledger: string; bytes: number | null; entradas: number; desaparecidas: number;
  con_tipo_pct: number; con_fecha_pct: number; con_destinatario_pct: number; ultima: string | null;
};
export type Salud = {
  ok: boolean; auth: boolean; ledgers: number; rotos: Record<string, string> | null;
  aviso: string | null; reconstrucciones: number;
  indexador: { error: string | null; fallos_seguidos: number; hace_s: number | null };
};
/** El censo crudo: quién es agente (y de qué humano responde), quién es humano
 *  escribiendo directo, y qué nombres son destinos de difusión. Lo sirve `/roster`
 *  sin reinterpretar — la clasificación (agente/humano/difusión) vive en el cliente. */
export type Roster = {
  agentes: { nombre: string | null; humano: string | null }[];
  humanos: { nombre: string | null; alias: string[] }[];
  difusion: string[];
};
/** `{ledger: última_llegada_leída}` del agente en `YO`. -1 = nunca leído. Solo
 *  lectura: la avanza la CLI u otro agente, nunca esta interfaz. */
export type Cursores = Record<string, number>;

async function pedir<T>(ruta: string, params: Record<string, unknown> = {}): Promise<T> {
  const u = new URL(ruta, location.origin);
  for (const [k, v] of Object.entries(params)) {
    if (v !== "" && v != null && v !== false) u.searchParams.set(k, String(v));
  }
  const r = await fetch(u, { headers: { "X-Llminbox-Token": getToken() } });
  if (r.status === 401) { clearToken(); location.reload(); }
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.headers.get("content-type")?.includes("json") ? r.json() : (r.text() as T);
}

export const api = {
  salud: () => pedir<Salud>("/health"),
  estado: () => pedir<Estado[]>("/stat"),
  roster: () => pedir<Roster>("/roster"),
  cursor: (agente: string) => pedir<Cursores>(`/cursor/${encodeURIComponent(agente)}`),
  entradas: (p: { ledger?: string; to?: string; actor?: string; tipo?: string;
                  q?: string; limit?: number; cuerpo?: boolean }) =>
    pedir<Entrada[]>("/entries", { ...p, cuerpo: p.cuerpo ?? true }),
  /** OJO: es de LECTURA. No avanza el cursor — eso es un POST aparte, a propósito:
   *  un GET que muta se lo dispara cualquiera, incluido un <img src> en otra página. */
  bandeja: (agente: string, limit = 30) =>
    pedir<string>(`/inbox/${encodeURIComponent(agente)}`, { limit }),
  marcarLeido: async (agente: string, hasta: Record<string, number>) => {
    const r = await fetch(`/inbox/${encodeURIComponent(agente)}/leido`, {
      method: "POST",
      headers: { "X-Llminbox-Token": getToken(), "Content-Type": "application/json" },
      body: JSON.stringify({ hasta }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },
};
