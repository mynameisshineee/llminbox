import { Fragment, useId, useState } from "react";
import type { Entrada } from "@/lib/api";
import { clasificar, humanoDe, type Censo } from "@/lib/censo";
import { hora, titular } from "@/lib/titular";
import { cn, tono } from "@/lib/utils";

/** Peso visual por tipo — la jerarquía que el 41%/2% pide [brief §5.3, §2.1]:
 *  HEARTBEAT es ruido de fondo (41% del volumen, cero decisión); REQUEST/HELD son
 *  los compromisos reales (el 0,2% que sí exige una decisión humana) y deben ganar
 *  el escaneo. Sin tipo → sin badge: un badge vacío es peor que ausencia, dada la
 *  deuda de tipado real (hasta 99% en un ledger). */
const PESO_TIPO: Record<string, string> = {
  HEARTBEAT: "border-linea text-apagado opacity-50",
  REQUEST: "border-current text-aviso",
  HELD: "border-current text-aviso",
  ACK: "border-current text-bien",
  DONE: "border-current text-bien",
};
const badgeTipo = (tipo: string) => PESO_TIPO[tipo] ?? "border-linea text-apagado";

function toneEstilo(nombre: string | null | undefined, l: number, c: number) {
  return { color: `oklch(${l} ${c} ${tono(nombre)})` } as const;
}

export function Fila({ e, yo, censo }: { e: Entrada; yo: string; censo: Censo }) {
  const [abierta, setAbierta] = useState(false);
  const idCuerpo = useId();
  const destinos = e.to ?? [];
  const mia = Boolean(yo) && (e.actor === yo || destinos.includes(yo));
  // `body` guarda la entrada ENTERA, cabecera incluida; arriba ya se muestra, así
  // que repetirla es ruido.
  const cuerpo = (e.body ?? "").replace(/^#{2,3} \[[^\n]*\n?/, "").trim();
  const largo = cuerpo.split("\n").length > 3 || cuerpo.length > 260;
  const claseActor = clasificar(censo, e.actor);
  const humanoActor = claseActor === "agente" ? humanoDe(censo, e.actor) : undefined;
  const heartbeat = e.tipo === "HEARTBEAT";

  const claseTitulo = cn(
    "mt-1.5 block max-w-[82ch] text-[15.5px] font-[450] leading-snug tracking-[-.005em] [overflow-wrap:anywhere]",
    heartbeat ? "text-apagado" : "text-tinta",
  );
  const textoTitular = titular(e.head, e.actor);

  return (
    <article
      className={cn(
        "border-b border-linea px-4 py-[11px] transition-colors duration-[var(--motion-duration-quick)] ease-[var(--motion-ease-standard)] hover:bg-panel motion-reduce:transition-none",
        mia && "shadow-[inset_3px_0_0_var(--color-lacre)] bg-[color-mix(in_srgb,var(--color-lacre)_4%,transparent)]",
      )}
    >
      <div className="flex flex-wrap items-center gap-2.5 text-xs">
        <span
          className="inline-flex items-center gap-1.5 font-mono text-[12.5px] font-semibold"
          style={e.actor ? toneEstilo(e.actor, 0.55, 0.11) : undefined}
        >
          <span aria-hidden="true" className="size-[7px] rounded-full" style={toneEstilo(e.actor, 0.62, 0.14)} />
          {e.actor ?? "?"}
        </span>
        {claseActor === "agente" && humanoActor && (
          <span className="text-[11px] font-normal text-apagado">· gestionado por {humanoActor}</span>
        )}
        {claseActor === "humano" && (
          <span className="rounded-[3px] border border-current px-1 py-px font-mono text-[9.5px] uppercase leading-[1.4] tracking-[.04em] text-bien">
            persona
          </span>
        )}
        {claseActor === "difusion" && (
          <span className="rounded-[3px] bg-lacre-d px-1 py-px font-mono text-[9.5px] uppercase leading-[1.4] tracking-[.04em] text-lacre">
            difusión
          </span>
        )}
        {destinos.length > 0 && (
          <>
            <span aria-hidden="true" className="text-apagado">
              →
            </span>
            <span className="font-mono text-[11.5px] text-apagado [overflow-wrap:anywhere]">
              {destinos.map((d, i) => {
                const kd = clasificar(censo, d);
                const humanoDest = kd === "agente" ? humanoDe(censo, d) : undefined;
                return (
                  <Fragment key={d}>
                    {i > 0 && " "}
                    <b
                      className={cn(
                        // `<b>` es bold por el reset del navegador (preservado por el preflight
                        // de Tailwind) — se neutraliza a normal y solo "yo"/difusión recuperan
                        // el peso, igual que `ui.html` (`.destino { font-weight:400 }`).
                        "font-normal",
                        (d === yo || kd === "difusion") && "font-semibold",
                        d === yo && "text-lacre",
                        kd === "difusion" && "inline-block rounded-[3px] bg-lacre-d px-1 text-tinta",
                      )}
                      style={kd === "agente" && d !== yo ? toneEstilo(d, 0.55, 0.11) : undefined}
                      title={humanoDest ? `gestionado por ${humanoDest}` : kd === "humano" ? "persona" : undefined}
                    >
                      {d}
                    </b>
                  </Fragment>
                );
              })}
            </span>
          </>
        )}
        {e.tipo && (
          <span className={cn("rounded border px-1.5 py-px font-mono text-[10px] tracking-wide", badgeTipo(e.tipo))}>
            {e.tipo}
          </span>
        )}
        <span className="ml-auto font-mono text-[11px] tabular-nums text-apagado">{hora(e.ts)}</span>
      </div>

      {largo ? (
        <button
          type="button"
          onClick={() => setAbierta((v) => !v)}
          aria-expanded={abierta}
          aria-controls={idCuerpo}
          title="Pulsa para ver el cuerpo entero"
          className={cn(
            claseTitulo,
            "cursor-pointer text-left outline-none hover:text-lacre focus-visible:ring-2 focus-visible:ring-lacre focus-visible:ring-offset-1",
            !abierta && "line-clamp-2",
          )}
        >
          {textoTitular}
        </button>
      ) : (
        <p className={claseTitulo}>{textoTitular}</p>
      )}

      {cuerpo && (
        <div className="relative mt-2">
          <pre
            id={idCuerpo}
            className={cn(
              "overflow-x-auto whitespace-pre-wrap rounded-fila border border-linea bg-panel px-3 py-2.5 font-mono text-xs leading-relaxed text-apagado [overflow-wrap:anywhere]",
              largo &&
                "transition-[max-height] duration-[var(--motion-duration-normal)] ease-[var(--motion-ease-standard)] motion-reduce:transition-none",
              abierta ? "max-h-[460px] overflow-y-auto" : largo ? "max-h-[5.1em] overflow-hidden" : "",
            )}
          >
            {cuerpo}
          </pre>
          {largo && !abierta && (
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-x-0 bottom-0 h-[2.2em] rounded-b-fila bg-gradient-to-b from-transparent to-panel"
            />
          )}
        </div>
      )}
      {largo && (
        <button
          type="button"
          onClick={() => setAbierta((v) => !v)}
          aria-expanded={abierta}
          aria-controls={idCuerpo}
          className="mt-1 rounded-sm text-xs text-lacre outline-none transition-colors duration-[var(--motion-duration-quick)] ease-[var(--motion-ease-standard)] hover:underline motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-lacre focus-visible:ring-offset-1"
        >
          {abierta ? "ver menos" : "ver más"}
        </button>
      )}
      <p className="mt-1.5 font-mono text-[10.5px] text-apagado [overflow-wrap:anywhere]">
        {e.ledger} · llegada #{e.arrival} · línea {e.line_no}
      </p>
    </article>
  );
}
