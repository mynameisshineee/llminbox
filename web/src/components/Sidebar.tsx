import { forwardRef } from "react";
import { Firma } from "@/components/Firma";
import type { Censo } from "@/lib/censo";
import { cn } from "@/lib/utils";

type FilaLedger = { ledger: string; entradas: number };

/** Sidebar — identidad, lista de ledgers ("todos" siempre primero) y marca.
 *  Doble uso: columna fija en desktop (≥760px), drawer `position:fixed` en móvil
 *  [brief §5.1]. El `ref` es para que el padre pueda mover el foco al primer
 *  elemento al abrir el drawer [brief §7, "Dialog no-modal-ligero"].
 *
 *  «Leer como» sube ARRIBA del todo y con su firma delante. Estaba al fondo, como
 *  un desplegable de ajuste, y es el control que decide qué enseña la aplicación
 *  entera: no es una preferencia, es el modo. Un producto cuya tesis es «cada
 *  agente tiene su propio cursor» no puede esconder de quién es el cursor. */
export const Sidebar = forwardRef<HTMLElement, {
  ledgers: FilaLedger[];
  totalLedgers: number;
  ledgerActivo: string;
  onSeleccionar: (ledger: string) => void;
  agentes: string[];
  yo: string;
  onCambiarYo: (nombre: string) => void;
  abierta: boolean;
  censo: Censo;
}>(function Sidebar(
  { ledgers, totalLedgers, ledgerActivo, onSeleccionar, agentes, yo, onCambiarYo, abierta, censo },
  ref,
) {
  const total = ledgers.reduce((a, x) => a + x.entradas, 0);
  const todas: FilaLedger[] = [{ ledger: "", entradas: total }, ...ledgers];

  return (
    <aside
      id="barra-lateral"
      ref={ref}
      className={cn(
        "fixed inset-y-0 left-0 z-20 flex w-[min(252px,82vw)] -translate-x-full flex-col overflow-y-auto border-r border-linea bg-panel transition-transform duration-[var(--motion-duration-drawer)] ease-[var(--motion-ease-standard)] motion-reduce:transition-none",
        "min-[760px]:static min-[760px]:z-auto min-[760px]:w-auto min-[760px]:translate-x-0 min-[760px]:transition-none",
        abierta && "translate-x-0",
      )}
    >
      <div className="p-2.5">
        <label htmlFor="leer-como" className="mb-1.5 ml-1 block text-[10px] font-semibold uppercase tracking-[.11em] text-tenue">
          Leyendo como
        </label>
        <div
          className={cn(
            "flex items-center gap-2.5 rounded-[10px] border px-2.5 py-2 transition-colors duration-[var(--motion-duration-quick)]",
            yo ? "border-linea bg-alzado" : "border-dashed border-linea bg-transparent",
          )}
        >
          {yo ? (
            <Firma nombre={yo} censo={censo} tam="lg" />
          ) : (
            <span
              aria-hidden="true"
              className="grid size-9 shrink-0 place-items-center rounded-[9px] border border-dashed border-linea text-base text-tenue"
            >
              ?
            </span>
          )}
          <div className="min-w-0 flex-1">
            <select
              id="leer-como"
              value={yo}
              onChange={(e) => onCambiarYo(e.target.value)}
              className="-ml-1 w-full cursor-pointer truncate rounded-md bg-transparent px-1 py-px text-[13.5px] font-semibold text-tinta outline-none hover:bg-panel focus-visible:ring-2 focus-visible:ring-lacre"
            >
              <option value="">elige un agente…</option>
              {agentes.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            <p className="ml-0 truncate text-[10.5px] text-tenue">
              {yo ? "lo tuyo se marca al margen" : "sin nadie no hay bandeja"}
            </p>
          </div>
        </div>
      </div>

      <nav aria-label="Ledgers" className="px-2 pb-2">
        <h2 className="mb-1 ml-1.5 text-[10px] font-semibold uppercase tracking-[.11em] text-tenue">Ledgers</h2>
        {todas.map((x) => (
          <button
            key={x.ledger || "todos"}
            type="button"
            onClick={() => onSeleccionar(x.ledger)}
            aria-current={ledgerActivo === x.ledger || undefined}
            className={cn(
              "flex w-full items-center gap-2 rounded-md px-2 py-[6px] text-left text-[13.5px] text-apagado outline-none transition-colors duration-[var(--motion-duration-quick)] ease-[var(--motion-ease-standard)] hover:bg-alzado hover:text-tinta motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-lacre focus-visible:ring-offset-1",
              ledgerActivo === x.ledger && "bg-alzado font-semibold text-tinta",
            )}
          >
            <span className="flex-1 truncate">{x.ledger || "todos"}</span>
            <span className="shrink-0 font-mono text-[11px] tabular-nums text-tenue">
              {x.entradas.toLocaleString("es")}
            </span>
          </button>
        ))}
      </nav>

      {/* La marca al pie y no en cabecera: el sitio de arriba lo gana el control que
          decide qué se ve. Nadie necesita que le recuerden dónde está cada vez. */}
      <div className="mt-auto border-t border-linea px-3.5 py-2.5">
        <b className="text-[12px] font-semibold tracking-[-.01em] text-apagado">llminbox</b>
        <p className="mt-px text-[10.5px] text-tenue">
          {totalLedgers > 0
            ? `${total.toLocaleString("es")} entradas · ${totalLedgers} ledgers`
            : "0 ledgers configurados"}
        </p>
      </div>
    </aside>
  );
});
